"""Backend für das Helpdesk-Dashboard.

Liefert Tickets, Kunden und Kundendoku aus data/testdaten/ und leitet
Fragen an die lokale KI (llama-server) weiter. Alles läuft lokal,
es werden keine externen Dienste angesprochen.

Starten (aus dem Repo-Hauptordner):
    uvicorn backend.app:app --reload
"""

import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi_offline import FastAPIOffline
from pydantic import BaseModel, Field

# --- Pfade und Konfiguration ---------------------------------------------

REPO = Path(__file__).resolve().parent.parent
DATEN = REPO / "data" / "testdaten"
FRONTEND = REPO / "frontend"

load_dotenv(REPO / ".env")

LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:8080").rstrip("/")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY", "")
KI_MOCK = os.getenv("KI_MOCK", "true").lower() == "true"
KI_TIMEOUT = float(os.getenv("KI_TIMEOUT", "120"))

SYSTEMPROMPT = (
    "Du bist ein Assistent im IT-Support. Antworte auf Deutsch, kurz und "
    "praxisnah in höchstens 5 Stichpunkten. Wenn du etwas nicht sicher weißt, "
    "sag das, statt zu raten."
)

app = FastAPIOffline(
    title="LF12 Helpdesk-Dashboard API",
    description="Schnittstelle zwischen Dashboard, Testdaten und lokaler KI.",
    version="0.1.0",
)


# --- Hilfsfunktionen -----------------------------------------------------

def lade_json(datei: str) -> list:
    """Liest eine JSON-Datei aus data/testdaten/ bei jedem Aufruf neu ein.

    So sind Änderungen an den Testdaten sofort sichtbar, ohne Neustart.
    """
    pfad = DATEN / datei
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(500, f"{datei} fehlt in data/testdaten/")
    except json.JSONDecodeError as fehler:
        raise HTTPException(500, f"{datei} ist kein gültiges JSON: {fehler}")


# --- Status --------------------------------------------------------------

@app.get("/api/status", tags=["Status"])
def status():
    """Zeigt, ob das Backend läuft und ob die KI erreichbar ist."""
    if KI_MOCK:
        return {"backend": "ok", "ki_modus": "mock", "ki_erreichbar": None}

    try:
        antwort = httpx.get(f"{LLAMA_URL}/health", timeout=3)
        erreichbar = antwort.status_code == 200
    except httpx.HTTPError:
        erreichbar = False
    return {"backend": "ok", "ki_modus": "llama", "ki_erreichbar": erreichbar}


# --- Tickets -------------------------------------------------------------

@app.get("/api/tickets", tags=["Tickets"])
def tickets(status: str | None = None, kunde: str | None = None):
    """Alle Tickets, optional gefiltert nach Status und/oder Kunde."""
    liste = lade_json("tickets.json")
    if status:
        liste = [t for t in liste if t["status"] == status]
    if kunde:
        liste = [t for t in liste if t["kunde"] == kunde]
    return liste


@app.get("/api/tickets/{ticket_id}", tags=["Tickets"])
def ticket(ticket_id: int):
    """Ein einzelnes Ticket anhand der Nummer."""
    for t in lade_json("tickets.json"):
        if t["id"] == ticket_id:
            return t
    raise HTTPException(404, f"Ticket #{ticket_id} nicht gefunden")


# --- Kunden --------------------------------------------------------------

@app.get("/api/kunden", tags=["Kunden"])
def kunden():
    """Alle Kunden."""
    return lade_json("kunden.json")


@app.get("/api/kunden/{kunde}/doku", tags=["Kunden"])
def kundendoku(kunde: str):
    """Kundendoku als Markdown-Text."""
    # Nur Kürzel aus kunden.json zulassen, damit niemand über den Pfad
    # an andere Dateien kommt (z. B. "../../.env").
    if kunde not in {k["kunde"] for k in lade_json("kunden.json")}:
        raise HTTPException(404, f"Kunde '{kunde}' nicht gefunden")

    pfad = DATEN / "doku" / f"{kunde}.md"
    if not pfad.exists():
        raise HTTPException(404, f"Keine Doku für '{kunde}' vorhanden")
    return {"kunde": kunde, "markdown": pfad.read_text(encoding="utf-8")}


# --- KI ------------------------------------------------------------------

class Frage(BaseModel):
    frage: str = Field(..., min_length=1, max_length=2000,
                       examples=["Ein Kunde meldet: Outlook startet nicht. Was kann ich tun?"])


@app.post("/api/ki/frage", tags=["KI"])
def ki_frage(eingabe: Frage):
    """Stellt der KI eine Frage.

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

    kopfzeilen = {"Authorization": f"Bearer {LLAMA_API_KEY}"} if LLAMA_API_KEY else {}
    anfrage = {
        "messages": [
            {"role": "system", "content": SYSTEMPROMPT},
            {"role": "user", "content": eingabe.frage},
        ],
        "temperature": 0.3,
    }

    try:
        r = httpx.post(f"{LLAMA_URL}/v1/chat/completions",
                       json=anfrage, headers=kopfzeilen, timeout=KI_TIMEOUT)
        r.raise_for_status()
        daten = r.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Die KI hat nicht rechtzeitig geantwortet")
    except httpx.HTTPError as fehler:
        raise HTTPException(502, f"KI nicht erreichbar unter {LLAMA_URL}: {fehler}")

    return {
        "antwort": daten["choices"][0]["message"]["content"],
        "modus": "llama",
        "dauer_ms": round((time.perf_counter() - start) * 1000),
        "tokens": daten.get("usage", {}).get("completion_tokens"),
    }


# --- Frontend ------------------------------------------------------------
# Wenn frontend/index.html existiert, liefert das Backend das Dashboard
# unter http://127.0.0.1:<APP_PORT>/ gleich mit aus. Muss am Ende stehen,
# damit /api/... und /docs Vorrang haben.

if (FRONTEND / "index.html").exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
