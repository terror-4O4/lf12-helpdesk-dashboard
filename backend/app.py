"""Backend für das Helpdesk-Dashboard.

Liefert Tickets, Kunden und Kundendoku und leitet Anfragen an die lokale
KI (llama-server) weiter. Alles läuft lokal, es werden keine externen
Dienste angesprochen.

Starten (aus dem Repo-Hauptordner):
    uvicorn backend.app:app --reload
"""

import ipaddress
import json
import os
import shutil
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi_offline import FastAPIOffline
from pydantic import BaseModel, Field

# --- Pfade und Konfiguration ---------------------------------------------

REPO = Path(__file__).resolve().parent.parent
DATEN = REPO / "data" / "testdaten"          # Ausgangsdaten, liegen im Repo
LAUFZEIT = REPO / "data" / "laufzeit"        # Arbeitskopie, NICHT im Repo
LAUFZEIT_TICKETS = LAUFZEIT / "tickets.json"
FRONTEND = REPO / "frontend"

load_dotenv(REPO / ".env")

LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:8080").rstrip("/")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY", "")
# Modellname für den llama-server im Router-Modus (Dateiname ohne .gguf).
# Leer lassen, wenn der llama-server mit genau einem Modell (-m) läuft.
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "").strip()
KI_MOCK = os.getenv("KI_MOCK", "true").lower() == "true"
KI_TIMEOUT = float(os.getenv("KI_TIMEOUT", "120"))


def pruefe_lokale_adresse(url: str) -> None:
    """Beendet das Backend, wenn die KI-Adresse nicht im lokalen Netz liegt.

    Erlaubt sind nur dieser Rechner (127.0.0.1, localhost) und private
    Netze (10.x, 172.16-31.x, 192.168.x). Damit können Ticketdaten das
    lokale Netz nie verlassen, auch nicht durch einen Fehler in der .env.
    Hostnamen werden aufgelöst, und ALLE zugehörigen Adressen müssen lokal sein.
    """
    teile = urlparse(url)
    if teile.scheme not in ("http", "https") or not teile.hostname:
        sys.exit(f"ABBRUCH: LLAMA_URL ist keine gültige Adresse: {url!r}")

    try:
        adressen = {info[4][0] for info in socket.getaddrinfo(teile.hostname, None)}
    except socket.gaierror:
        sys.exit(f"ABBRUCH: LLAMA_URL-Host {teile.hostname!r} lässt sich nicht auflösen")

    for adresse in adressen:
        ip = ipaddress.ip_address(adresse.split("%")[0])
        if not (ip.is_loopback or ip.is_private) or ip.is_link_local:
            sys.exit(
                f"ABBRUCH: LLAMA_URL zeigt auf {adresse} ({teile.hostname}). "
                "Erlaubt sind nur lokale Adressen. Ticketdaten dürfen das "
                "lokale Netz nicht verlassen."
            )


# Prüfung beim Start, unabhängig von KI_MOCK: Eine falsche Adresse soll
# sofort auffallen und nicht erst, wenn jemand den Mock abschaltet.
pruefe_lokale_adresse(LLAMA_URL)

app = FastAPIOffline(
    title="LF12 Helpdesk-Dashboard API",
    description="Schnittstelle zwischen Dashboard, Testdaten und lokaler KI.",
    version="0.2.0",
)


# --- Daten lesen und schreiben -------------------------------------------

def lade_json(pfad: Path) -> list:
    """Liest eine JSON-Datei bei jedem Aufruf neu ein (Änderungen sofort sichtbar)."""
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(500, f"{pfad.name} fehlt in {pfad.parent.relative_to(REPO)}/")
    except json.JSONDecodeError as fehler:
        raise HTTPException(500, f"{pfad.name} ist kein gültiges JSON: {fehler}")


def stelle_arbeitskopie_bereit(neu: bool = False) -> None:
    """Kopiert die Testtickets nach data/laufzeit/, falls dort noch keine liegen.

    Das Backend arbeitet nur mit der Arbeitskopie. So verändern KI-Analysen
    nie die Testdaten im Repo, und man kann jederzeit neu anfangen.
    """
    LAUFZEIT.mkdir(parents=True, exist_ok=True)
    if neu or not LAUFZEIT_TICKETS.exists():
        shutil.copyfile(DATEN / "tickets.json", LAUFZEIT_TICKETS)


def lade_tickets() -> list:
    stelle_arbeitskopie_bereit()
    return lade_json(LAUFZEIT_TICKETS)


def speichere_tickets(liste: list) -> None:
    """Schreibt erst in eine Hilfsdatei und ersetzt dann das Original.

    Bricht das Schreiben ab, bleibt die alte Datei heil.
    """
    tmp = LAUFZEIT_TICKETS.with_suffix(".tmp")
    tmp.write_text(json.dumps(liste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, LAUFZEIT_TICKETS)


def lade_kunden() -> list:
    return lade_json(DATEN / "kunden.json")


def finde_ticket(liste: list, ticket_id: int) -> dict:
    for t in liste:
        if t["id"] == ticket_id:
            return t
    raise HTTPException(404, f"Ticket #{ticket_id} nicht gefunden")


def doku_abschnitt(kunde: str | None, ueberschrift: str) -> str:
    """Gibt einen Abschnitt (## Überschrift) aus der Kundendoku zurück, sonst ''."""
    if not kunde:
        return ""
    pfad = DATEN / "doku" / f"{kunde}.md"
    if not pfad.exists():
        return ""
    abschnitt, drin = [], False
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if zeile.startswith("## "):
            drin = zeile[3:].strip() == ueberschrift
            continue
        if drin:
            abschnitt.append(zeile)
    return "\n".join(abschnitt).strip()


# --- KI-Anbindung --------------------------------------------------------

def frage_llama(nachrichten: list, antwortformat: dict | None = None,
                temperatur: float = 0.3) -> tuple[str, int | None]:
    """Schickt Nachrichten an den llama-server. Gibt (Text, Anzahl Tokens) zurück."""
    kopfzeilen = {"Authorization": f"Bearer {LLAMA_API_KEY}"} if LLAMA_API_KEY else {}
    anfrage = {"messages": nachrichten, "temperature": temperatur}
    if LLAMA_MODEL:
        # Im Router-Modus wählt der llama-server anhand dieses Feldes das Modell
        anfrage["model"] = LLAMA_MODEL
    if antwortformat:
        anfrage["response_format"] = antwortformat

    try:
        # trust_env=False: keine Proxy-Einstellungen des Systems verwenden,
        # die Anfrage geht immer direkt an den lokalen llama-server.
        r = httpx.post(f"{LLAMA_URL}/v1/chat/completions",
                       json=anfrage, headers=kopfzeilen, timeout=KI_TIMEOUT,
                       trust_env=False)
        r.raise_for_status()
        daten = r.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Die KI hat nicht rechtzeitig geantwortet")
    except httpx.HTTPStatusError as fehler:
        # Server erreichbar, lehnt die Anfrage aber ab: Grund mit ausgeben
        code, text = fehler.response.status_code, fehler.response.text[:200]
        hinweis = ""
        if code == 401:
            hinweis = " (LLAMA_API_KEY in der .env prüfen)"
        elif code == 400 and "model" in text:
            hinweis = " (LLAMA_MODEL in der .env setzen, Router-Modus)"
        raise HTTPException(502, f"KI-Server lehnt ab ({code}){hinweis}: {text}")
    except httpx.HTTPError as fehler:
        raise HTTPException(502, f"KI nicht erreichbar unter {LLAMA_URL}: {fehler}")

    return (daten["choices"][0]["message"]["content"],
            daten.get("usage", {}).get("completion_tokens"))


# --- Status --------------------------------------------------------------

@app.get("/api/status", tags=["Status"])
def status():
    """Zeigt, ob das Backend läuft und ob die KI erreichbar ist."""
    if KI_MOCK:
        return {"backend": "ok", "ki_modus": "mock", "ki_erreichbar": None}

    try:
        antwort = httpx.get(f"{LLAMA_URL}/health", timeout=3, trust_env=False)
        erreichbar = antwort.status_code == 200
    except httpx.HTTPError:
        erreichbar = False
    return {"backend": "ok", "ki_modus": "llama", "ki_erreichbar": erreichbar,
            "ki_modell": LLAMA_MODEL or None}


# --- Tickets -------------------------------------------------------------

@app.get("/api/tickets", tags=["Tickets"])
def tickets(status: str | None = None, kunde: str | None = None):
    """Alle Tickets, optional gefiltert nach Status und/oder Kunde."""
    liste = lade_tickets()
    if status:
        liste = [t for t in liste if t["status"] == status]
    if kunde:
        liste = [t for t in liste if t["kunde"] == kunde]
    return liste


@app.get("/api/tickets/{ticket_id}", tags=["Tickets"])
def ticket(ticket_id: int):
    """Ein einzelnes Ticket anhand der Nummer."""
    return finde_ticket(lade_tickets(), ticket_id)


@app.post("/api/testdaten/zuruecksetzen", tags=["Tickets"])
def testdaten_zuruecksetzen():
    """Verwirft alle Änderungen (z. B. KI-Analysen) und lädt die Testtickets neu."""
    stelle_arbeitskopie_bereit(neu=True)
    return {"zurueckgesetzt": True, "tickets": len(lade_tickets())}


# --- Kunden --------------------------------------------------------------

@app.get("/api/kunden", tags=["Kunden"])
def kunden():
    """Alle Kunden."""
    return lade_kunden()


@app.get("/api/kunden/{kunde}/doku", tags=["Kunden"])
def kundendoku(kunde: str):
    """Kundendoku als Markdown-Text."""
    # Nur Kürzel aus kunden.json zulassen, damit niemand über den Pfad
    # an andere Dateien kommt (z. B. "../../.env").
    if kunde not in {k["kunde"] for k in lade_kunden()}:
        raise HTTPException(404, f"Kunde '{kunde}' nicht gefunden")

    pfad = DATEN / "doku" / f"{kunde}.md"
    if not pfad.exists():
        raise HTTPException(404, f"Keine Doku für '{kunde}' vorhanden")
    return {"kunde": kunde, "markdown": pfad.read_text(encoding="utf-8")}


# --- KI: freie Frage -----------------------------------------------------

SYSTEMPROMPT_FRAGE = (
    "Du bist ein Assistent im IT-Support. Antworte auf Deutsch, kurz und "
    "praxisnah in höchstens 5 Stichpunkten. Wenn du etwas nicht sicher weißt, "
    "sag das, statt zu raten."
)


class Frage(BaseModel):
    frage: str = Field(..., min_length=1, max_length=2000,
                       examples=["Ein Kunde meldet: Outlook startet nicht. Was kann ich tun?"])


@app.post("/api/ki/frage", tags=["KI"])
def ki_frage(eingabe: Frage):
    """Stellt der KI eine freie Frage.

    Mit KI_MOCK=true kommt eine Beispielantwort (zum Entwickeln ohne KI-Server),
    mit KI_MOCK=false antwortet der llama-server aus LLAMA_URL.
    """
    start = time.perf_counter()

    if KI_MOCK:
        antwort = (
            "[Mock-Antwort] Das ist eine Beispielantwort. Sobald KI_MOCK=false "
            f"gesetzt ist, antwortet hier die lokale KI auf: \"{eingabe.frage}\""
        )
        return {"antwort": antwort, "modus": "mock",
                "dauer_ms": round((time.perf_counter() - start) * 1000)}

    text, tokens = frage_llama([
        {"role": "system", "content": SYSTEMPROMPT_FRAGE},
        {"role": "user", "content": eingabe.frage},
    ])
    return {"antwort": text, "modus": "llama",
            "dauer_ms": round((time.perf_counter() - start) * 1000), "tokens": tokens}


# --- KI: Ticket-Analyse --------------------------------------------------

PRIORITAETEN = ["niedrig", "mittel", "hoch", "sehr_hoch"]
KATEGORIEN = ["Software", "Hardware", "Netzwerk", "Drucker",
              "Benutzerkonto", "E-Mail", "Spam", "Sonstiges"]

SYSTEMPROMPT_ANALYSE = f"""Du bewertest eingehende Tickets im IT-Support eines Systemhauses.

Priorität (wähle genau eine):
- sehr_hoch: Geschäftsbetrieb steht oder mehrere Nutzer bzw. eine ganze Abteilung sind betroffen, kein Workaround (z. B. Server, Internet, Lager oder Warenausgang fällt aus)
- hoch: Eine Person kann nicht arbeiten oder eine wichtige Funktion fällt aus
- mittel: Arbeit ist eingeschränkt, aber ein Workaround ist möglich
- niedrig: Frage, Wunsch, kosmetisches Problem oder Spam

Spam: true bei Phishing, Werbung, Kettenbriefen oder Nachrichten ohne echtes IT-Anliegen. Typische Merkmale von Phishing sind Zeitdruck, Drohung mit Sperrung und die Aufforderung, Zugangsdaten über einen Link einzugeben. Spam bekommt immer die Priorität niedrig und die Kategorie Spam.

Kategorie (wähle genau eine): {", ".join(KATEGORIEN)}

Berücksichtige die Besonderheiten des Kunden, falls angegeben.
Antworte nur mit dem JSON-Objekt. Die Begründung ist ein kurzer deutscher Satz."""

# Erzwingt bei llama.cpp gültiges JSON mit genau diesen Feldern und Werten
ANALYSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "ticket_analyse",
        "schema": {
            "type": "object",
            "properties": {
                "prioritaet": {"type": "string", "enum": PRIORITAETEN},
                "spam": {"type": "boolean"},
                "kategorie": {"type": "string", "enum": KATEGORIEN},
                "begruendung": {"type": "string", "maxLength": 300},
            },
            "required": ["prioritaet", "spam", "kategorie", "begruendung"],
            "additionalProperties": False,
        },
    },
}

MOCK_SPAM_WOERTER = ("bestätigen sie", "link", "gesperrt", "gewonnen", "gewinn")


def analysiere_mock(t: dict) -> dict:
    """Einfache Regel statt KI, damit das Frontend ohne KI-Server testen kann."""
    text = f"{t['titel']} {t['beschreibung']}".lower()
    if any(w in text for w in MOCK_SPAM_WOERTER):
        return {"prioritaet": "niedrig", "spam": True, "kategorie": "Spam",
                "begruendung": "[Mock] Enthält typische Spam-Wörter."}
    return {"prioritaet": "mittel", "spam": False, "kategorie": "Sonstiges",
            "begruendung": "[Mock] Platzhalter-Bewertung ohne KI."}


def analysiere_llama(t: dict) -> tuple[dict, int | None]:
    kunde = next((k for k in lade_kunden() if k["kunde"] == t["kunde"]), None)
    besonderheiten = doku_abschnitt(t["kunde"], "Besonderheiten")

    ticket_text = (
        f"Kunde: {kunde['name'] if kunde else 'unbekannt'}\n"
        f"Besonderheiten des Kunden: {besonderheiten or 'keine'}\n"
        f"Titel: {t['titel']}\n"
        f"Beschreibung: {t['beschreibung']}"
    )
    text, tokens = frage_llama(
        [{"role": "system", "content": SYSTEMPROMPT_ANALYSE},
         {"role": "user", "content": ticket_text}],
        antwortformat=ANALYSE_FORMAT,
        temperatur=0,
    )

    # Doppelt prüfen: Auch wenn das Format erzwungen ist, nichts ungeprüft übernehmen
    try:
        ergebnis = json.loads(text)
        assert ergebnis["prioritaet"] in PRIORITAETEN
        assert ergebnis["kategorie"] in KATEGORIEN
        assert isinstance(ergebnis["spam"], bool)
        ergebnis["begruendung"] = str(ergebnis.get("begruendung", ""))[:300]
    except (json.JSONDecodeError, KeyError, AssertionError, TypeError):
        raise HTTPException(502, f"KI-Antwort hat ein ungültiges Format: {text[:200]}")

    if ergebnis["spam"]:
        ergebnis["prioritaet"], ergebnis["kategorie"] = "niedrig", "Spam"
    return ergebnis, tokens


@app.post("/api/tickets/{ticket_id}/analyse", tags=["KI"])
def ticket_analyse(ticket_id: int, speichern: bool = True):
    """Lässt die KI ein Ticket bewerten: Priorität, Spam, Kategorie, Begründung.

    Mit speichern=true wird das Ergebnis in den KI-Block des Tickets geschrieben.
    Die Priorität des Tickets wird nur übernommen, wenn sie nicht von Hand
    geändert wurde (prioritaet_quelle "manuell" hat Vorrang).
    """
    start = time.perf_counter()
    liste = lade_tickets()
    t = finde_ticket(liste, ticket_id)

    if KI_MOCK:
        ergebnis, tokens, modus = analysiere_mock(t), None, "mock"
    else:
        (ergebnis, tokens), modus = analysiere_llama(t), "llama"

    if speichern:
        alt = t.get("ki") or {}
        t["ki"] = {
            "prioritaet": ergebnis["prioritaet"],
            "spam": ergebnis["spam"],
            "kategorie": ergebnis["kategorie"],
            "begruendung": ergebnis["begruendung"],
            # Lösungsvorschlag kommt später per RAG, bis dahin unverändert lassen
            "loesungsvorschlag": alt.get("loesungsvorschlag"),
            "aehnliche_tickets": alt.get("aehnliche_tickets", []),
        }
        if t.get("prioritaet_quelle") != "manuell":
            t["prioritaet"] = ergebnis["prioritaet"]
            t["prioritaet_quelle"] = "ki"
        speichere_tickets(liste)

    return {
        "ticket_id": ticket_id,
        "ergebnis": ergebnis,
        "prioritaet_ticket": t["prioritaet"],
        "gespeichert": speichern,
        "modus": modus,
        "dauer_ms": round((time.perf_counter() - start) * 1000),
        "tokens": tokens,
    }


# --- Frontend ------------------------------------------------------------
# Wenn frontend/index.html existiert, liefert das Backend das Dashboard
# unter http://127.0.0.1:<APP_PORT>/ gleich mit aus. Muss am Ende stehen,
# damit /api/... und /docs Vorrang haben.

if (FRONTEND / "index.html").exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
