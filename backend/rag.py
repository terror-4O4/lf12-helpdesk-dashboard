"""Wissensbasis aus gelösten Tickets und Suche nach ähnlichen Fällen (RAG).

Ablauf:
1. Jedes gelöste Ticket (geschlossen, mit Lösungsweg, kein Spam) wird einmal
   in einen Zahlenvektor umgewandelt (Embedding). Ähnliche Probleme bekommen
   ähnliche Vektoren, auch wenn andere Wörter benutzt werden.
2. Die Vektoren liegen in data/laufzeit/wissensbasis.json. Neue oder geänderte
   Tickets werden beim nächsten Suchen automatisch ergänzt, die Wissensbasis
   wächst also mit jedem abgeschlossenen Ticket.
3. Für ein neues Ticket wird ebenfalls ein Vektor berechnet und mit allen
   Fällen verglichen (Kosinus-Ähnlichkeit). Fälle beim selben Kunden bekommen
   einen kleinen Bonus. Was unter der Schwelle liegt, gilt als "kein passender Fall".

Eine Vektordatenbank ist bei einigen Dutzend Tickets nicht nötig, der
Vergleich in Python dauert unter einer Millisekunde.
"""

import hashlib
import json
import math
import re
from pathlib import Path
from threading import Lock

import httpx

from backend import eingang
from backend.speicher import schreibe_atomar

# EmbeddingGemma erwartet eine Aufgabe vor dem Text. Für den Vergleich
# Ticket mit Ticket ist "sentence similarity" passend (beide Seiten gleich).
# Anderes Embedding-Modell: EMBED_PRAEFIX in der .env anpassen.
STANDARD_PRAEFIX = "task: sentence similarity | query: "

# Größe der Ersatz-Vektoren im Mock-Modus
MOCK_DIMENSIONEN = 512


def ticket_text(t: dict) -> str:
    """Das Problem, wie der Kunde es beschreibt. Ursache und Lösung gehören
    nicht dazu, denn verglichen wird Problem mit Problem."""
    return f"{t['titel']}\n{t['beschreibung']}"


def fall_text(t: dict, mit_ursache: bool = False) -> str:
    """Text eines gelösten Falls für die Wissensbasis.

    Standard ist nur das Problem (wie ticket_text). Mit mit_ursache=True kommt
    die Ursache dazu, damit auch Tickets mit anderen Symptomen, aber gleicher
    Ursache gefunden werden (z. B. Warnung "Postfach fast voll" gegen den Fall
    "Speichergrenze erreicht"). Das neue Ticket hat noch keine Ursache und wird
    weiter mit ticket_text verglichen.
    """
    text = ticket_text(t)
    ursache = (t.get("ursache") or "").strip()
    return f"{text}\nUrsache: {ursache}" if mit_ursache and ursache else text


def ist_fall(t: dict) -> bool:
    """Gehört das Ticket in die Wissensbasis?"""
    return (
        t.get("status") == "geschlossen"
        and bool((t.get("loesungsweg") or "").strip())
        and not eingang.ist_spam(t)
    )


def normiere(v: list[float]) -> list[float]:
    laenge = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / laenge for x in v]


def aehnlichkeit(a: list[float], b: list[float]) -> float:
    """Kosinus-Ähnlichkeit zweier normierter Vektoren (1 = gleich, 0 = nichts gemeinsam)."""
    return sum(x * y for x, y in zip(a, b))


# --- Embeddings ---------------------------------------------------------------

class EmbeddingFehler(Exception):
    pass


class Einbetter:
    """Holt Embeddings vom llama-server (Endpunkt /v1/embeddings).

    Im Mock-Modus wird stattdessen ein einfacher Wort-Vektor gebildet. Der
    findet nur Tickets mit gleichen Wörtern, reicht aber zum Entwickeln.
    """

    def __init__(self, url: str, api_key: str = "", modell: str = "",
                 timeout: float = 60, mock: bool = False, praefix: str = STANDARD_PRAEFIX):
        self.url = url.rstrip("/")
        self.praefix = praefix
        self.api_key = api_key
        self.modell = modell
        self.timeout = timeout
        self.mock = mock

    @property
    def kennung(self) -> str:
        """Ändert sich das Modell, müssen alle Vektoren neu berechnet werden."""
        return "mock-woerter-v1" if self.mock else f"{self.modell or 'standard'}|{self.praefix}"

    def einbetten(self, texte: list[str]) -> list[list[float]]:
        if not texte:
            return []
        if self.mock:
            return [mock_vektor(t) for t in texte]

        kopf = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        anfrage = {"input": [self.praefix + t for t in texte]}
        if self.modell:
            anfrage["model"] = self.modell
        try:
            # trust_env=False: nie über einen System-Proxy, immer direkt ins lokale Netz
            r = httpx.post(f"{self.url}/v1/embeddings", json=anfrage, headers=kopf,
                           timeout=self.timeout, trust_env=False)
            r.raise_for_status()
            daten = sorted(r.json()["data"], key=lambda d: d["index"])
        except httpx.HTTPStatusError as fehler:
            code = fehler.response.status_code
            hinweis = " (LLAMA_API_KEY prüfen)" if code == 401 else ""
            raise EmbeddingFehler(f"Embedding-Server lehnt ab ({code}){hinweis}: "
                                  f"{fehler.response.text[:200]}")
        except httpx.HTTPError as fehler:
            raise EmbeddingFehler(f"Embedding-Server nicht erreichbar unter {self.url}: {fehler}")
        except (KeyError, ValueError) as fehler:
            raise EmbeddingFehler(f"Unerwartete Antwort vom Embedding-Server: {fehler}")
        return [normiere(d["embedding"]) for d in daten]


_WORT = re.compile(r"[a-zäöüß0-9]+")
_ENDUNGEN = ("ungen", "ung", "en", "er", "e", "n", "s")


def _stamm(wort: str) -> str:
    for endung in _ENDUNGEN:
        if wort.endswith(endung) and len(wort) - len(endung) >= 4:
            return wort[: -len(endung)]
    return wort


def mock_vektor(text: str) -> list[float]:
    """Wort-Vektor für den Mock: jedes Wort (grob auf den Stamm gekürzt) zählt in ein Fach."""
    v = [0.0] * MOCK_DIMENSIONEN
    for wort in _WORT.findall(text.lower()):
        if len(wort) < 4:
            continue
        fach = int(hashlib.md5(_stamm(wort).encode()).hexdigest(), 16) % MOCK_DIMENSIONEN
        v[fach] += 1.0
    return normiere(v)


# --- Wissensbasis (Vektoren zwischenspeichern) -------------------------------------

class Wissensbasis:
    def __init__(self, pfad: Path):
        self.pfad = pfad
        self._datei_lock = Lock()

    def _lade(self) -> dict:
        with self._datei_lock:
            try:
                return json.loads(self.pfad.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                return {}

    def _speichere(self, daten: dict) -> None:
        with self._datei_lock:
            schreibe_atomar(self.pfad, json.dumps(daten))

    def vektoren(self, faelle: list[dict], einbetter: Einbetter,
                 mit_ursache: bool = False) -> dict[int, list[float]]:
        """Vektoren aller Fälle. Berechnet nur, was neu ist oder sich geändert hat."""
        daten = self._lade()
        if daten.get("kennung") != einbetter.kennung:
            daten = {"kennung": einbetter.kennung, "eintraege": {}}
        alt = daten["eintraege"]

        neu, fehlend = {}, []
        for t in faelle:
            text = fall_text(t, mit_ursache)
            pruefsumme = hashlib.sha256(text.encode()).hexdigest()[:16]
            eintrag = alt.get(str(t["id"]))
            if eintrag and eintrag["pruefsumme"] == pruefsumme:
                neu[str(t["id"])] = eintrag
            else:
                fehlend.append((t, pruefsumme, text))

        if fehlend:
            vektoren = einbetter.einbetten([text for _, _, text in fehlend])
            for (t, pruefsumme, _), vektor in zip(fehlend, vektoren):
                neu[str(t["id"])] = {"pruefsumme": pruefsumme, "vektor": vektor}

        if fehlend or set(neu) != set(alt):
            daten["eintraege"] = neu
            self._speichere(daten)
        return {int(k): v["vektor"] for k, v in neu.items()}


def suche(anfrage_vektor: list[float], faelle: list[dict], vektoren: dict[int, list[float]],
          kunde: str | None, anzahl: int = 3, kundenbonus: float = 0.05,
          schwelle: float = 0.5) -> list[dict]:
    """Die ähnlichsten Fälle, bester zuerst. Nur Fälle über der Schwelle.

    "aehnlichkeit" ist der reine Vergleichswert, "wert" enthält den Bonus für
    denselben Kunden und bestimmt die Reihenfolge.
    """
    treffer = []
    for t in faelle:
        if t["id"] not in vektoren:
            continue
        a = aehnlichkeit(anfrage_vektor, vektoren[t["id"]])
        gleicher_kunde = kunde is not None and t.get("kunde") == kunde
        wert = a + (kundenbonus if gleicher_kunde else 0.0)
        treffer.append({"id": t["id"], "aehnlichkeit": round(a, 3), "wert": round(wert, 3),
                        "gleicher_kunde": gleicher_kunde})
    treffer.sort(key=lambda x: (-x["wert"], x["id"]))
    return [x for x in treffer if x["wert"] >= schwelle][:anzahl]
