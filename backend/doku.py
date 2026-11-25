"""Lokale Suche in den Markdown-Abschnitten einer Kundendokumentation."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


_WORT = re.compile(r"[a-zäöüß0-9]+", re.IGNORECASE)
_UEBERSCHRIFT = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", re.IGNORECASE)
_ZUGANG = re.compile(
    r"\b(passw[öo]rt\w*|kennw[öo]rt\w*|zugangsdaten|login-daten|"
    r"passwortmanager\w*|admin-zugang\w*|api[- ]key\w*|geheimschlüssel\w*)\b",
    re.IGNORECASE,
)
_VERWEIS = re.compile(
    r'[-*]\s*([^:\n]+):\s*siehe Passwortmanager,\s*Eintrag\s+"([^"\n]+)"',
    re.IGNORECASE,
)
_STOPP = set(
    "aber alle auch auf aus beim bei bitte das dass dem den der des die diese dort eine einem "
    "einen einer euch falls frage für gibt hat haben hier ich ihre im ins ist kann kannst "
    "kunde kunden kundendoku kundendokumentation lautet man mehr mein mir mit muss "
    "nach nur oder seit sich sie sind soll sonst sollst steht und uns unser vom von vor "
    "wann war was welches welche welchem welchen wenn werden wer wie wird wo wohin zum zur".split()
)
_ENDUNGEN = ("ungen", "ung", "eren", "es", "en", "er", "e", "n", "s")

KEINE_QUELLE = "In der ausgewählten Kundendokumentation gibt es keine passende Fundstelle."
PASSWORT_HINWEIS = "Zugangsdaten findest du im Passwortmanager. Wähle dort den passenden Kundeneintrag."


@dataclass(frozen=True)
class Abschnitt:
    titel: str
    quelle: str
    text: str

    def als_quelle(self) -> dict:
        links = []
        for titel, url in _LINK.findall(self.text):
            try:
                ziel = urlsplit(url)
                if ziel.hostname and not ziel.username and not ziel.password:
                    links.append({"titel": titel, "url": url})
            except ValueError:
                continue
        return {
            "titel": self.titel,
            "quelle": self.quelle,
            "text": _LINK.sub(r"\1", self.text),
            "links": links,
        }


def abschnitte(pfad: Path) -> list[Abschnitt]:
    """Liest jeden Abschnitt zusammen mit seiner nachvollziehbaren Fundstelle."""
    try:
        markdown = pfad.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []

    marken = list(_UEBERSCHRIFT.finditer(markdown))
    ziele = {}
    ergebnis = []
    for i, marke in enumerate(marken):
        titel = marke[1].strip()
        ende = marken[i + 1].start() if i + 1 < len(marken) else len(markdown)
        text = markdown[marke.end():ende].strip()
        if not text:
            continue
        ascii_titel = unicodedata.normalize("NFKD", titel.lower().replace("ß", "ss"))
        ascii_titel = ascii_titel.encode("ascii", "ignore").decode("ascii")
        anker = re.sub(r"[^a-z0-9]+", "-", ascii_titel).strip("-") or "abschnitt"
        vorkommen = ziele.get(anker, 0) + 1
        ziele[anker] = vorkommen
        if vorkommen > 1:
            anker = f"{anker}-{vorkommen - 1}"
        ergebnis.append(Abschnitt(titel, f"doku/{pfad.name}#{anker}", text))
    return ergebnis


def _stamm(wort: str) -> str:
    for endung in _ENDUNGEN:
        if wort.endswith(endung) and len(wort) - len(endung) >= 4:
            return wort[:-len(endung)]
    return wort


def _begriffe(text: str) -> set[str]:
    return {
        _stamm(wort) for wort in _WORT.findall(text.lower())
        if len(wort) >= 3 and wort not in _STOPP
    }


def _treffer(anfrage: set[str], text: str) -> set[str]:
    woerter = _begriffe(text)
    return {
        wort for wort in anfrage
        if wort in woerter or (
            len(wort) >= 4 and any(w.startswith(wort) for w in woerter)
        )
    }


def ist_zugangsfrage(text: str) -> bool:
    return bool(_ZUGANG.search(text))


def fremder_kunde(frage: str, kunde: str, kunden: list[dict]) -> bool:
    """Erkennt ausdrücklich genannte andere Kunden in einer freien Doku-Frage."""
    for eintrag in kunden:
        kuerzel = eintrag["kunde"]
        if kuerzel == kunde:
            continue
        sichtbarer_name = eintrag["name"]
        if re.search(rf"\b{re.escape(sichtbarer_name)}", frage, re.IGNORECASE):
            return True
        # Kurze oder allgemeine Kürzel können Teil der eigentlichen Frage sein.
        if kuerzel in {"bau", "praxis", "logistik"}:
            muster = rf'\b(?:kunde\s+|für\s+|bei\s+){re.escape(kuerzel)}\b'
        else:
            muster = rf"\b{re.escape(kuerzel)}(?:es|s)?\b"
        if re.search(muster, frage, re.IGNORECASE):
            return True
    return False


def suche(dokument: list[Abschnitt], frage: str, *, titel: str = "") -> list[Abschnitt]:
    """Sortiert bis zu drei Treffer nach Begriffen in Überschrift und Abschnitt."""
    anfrage = _begriffe(frage)
    titel_begriffe = _begriffe(titel)
    bewertet = []
    for abschnitt in dokument:
        if abschnitt.titel.casefold() == "zugangsdaten":
            continue
        text_treffer = _treffer(anfrage, abschnitt.text)
        titel_treffer = _treffer(anfrage, abschnitt.titel)
        ticket_treffer = titel_begriffe & (text_treffer | titel_treffer)
        if text_treffer or titel_treffer:
            score = len(text_treffer) + 2 * len(titel_treffer) + len(ticket_treffer)
            bewertet.append((score, abschnitt))
    bewertet.sort(key=lambda eintrag: -eintrag[0])
    return [abschnitt for _, abschnitt in bewertet[:3]]


def passwortverweise(dokument: list[Abschnitt], frage: str) -> list[Abschnitt]:
    """Stellt ausschließlich explizit erfasste Passwortmanager-Verweise bereit."""
    suchbegriffe = _begriffe(_ZUGANG.sub("", frage))
    for abschnitt in dokument:
        if abschnitt.titel.casefold() != "zugangsdaten":
            continue
        verweise = []
        for zeile in abschnitt.text.splitlines():
            zeile = zeile.strip()
            verweis = _VERWEIS.fullmatch(zeile)
            if verweis:
                begriffe = len(_treffer(suchbegriffe, verweis[1] + " " + verweis[2]))
                verweise.append((begriffe, zeile))
        bester = max((anzahl for anzahl, _ in verweise), default=0)
        if suchbegriffe:
            zeilen = [zeile for anzahl, zeile in verweise if anzahl == bester and anzahl > 0]
        else:
            zeilen = [zeile for _, zeile in verweise]
        if zeilen:
            return [Abschnitt(abschnitt.titel, abschnitt.quelle, "\n".join(zeilen))]
    return []
