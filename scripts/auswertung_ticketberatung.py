"""Prüft neue Tickets über die Dashboard-API mit dem echten lokalen Beratungsmodell."""

import argparse
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dotenv import load_dotenv
from fastapi.testclient import TestClient


REPO = Path(__file__).resolve().parents[1]
BERICHTE = REPO / "data" / "laufzeit" / "auswertung"


def pruefe_fall(client, app, fall):
    """Lässt Suche und Quellen unverändert und vergleicht nur die Formulierung der Beratung."""
    eingang = {feld: fall[feld] for feld in ("kunde", "titel", "beschreibung")}
    ticket = client.post("/api/tickets", json=eingang).raise_for_status().json()
    vergleich = {}
    original = app.ticketfragen.beratung

    def beratung_mit_vergleich(*args, **kwargs):
        parameter = inspect.signature(original).bind(*args, **kwargs)
        mit_modell = original(*parameter.args, **parameter.kwargs)
        parameter.arguments["modell"] = None
        if "nachweis" in parameter.arguments:
            parameter.arguments["nachweis"] = {}
        ohne_modell = original(*parameter.args, **parameter.kwargs)
        vergleich["ohne_beratungsmodell"] = ohne_modell[0]
        vergleich["abweichend"] = mit_modell[0] != ohne_modell[0]
        return mit_modell

    echte_anfrage = app.frage_beratungsmodell
    rohantworten = []

    def modell_protokollieren(*args, **kwargs):
        antwort, tokens = echte_anfrage(*args, **kwargs)
        rohantworten.append(antwort)
        return antwort, tokens

    with patch.object(app.ticketfragen, "beratung", beratung_mit_vergleich), \
            patch.object(app, "frage_beratungsmodell", modell_protokollieren):
        antwort = client.post(f"/api/tickets/{ticket['id']}/frage", json={"frage": fall["frage"]})
        antwort.raise_for_status()
        daten = antwort.json()
    return {"id": fall["id"], **eingang, "frage": fall["frage"], "antwort": daten["antwort"],
            "quellen": [q["quelle"] for q in daten["quellen"]], "modus": daten["modus"],
            "dauer_ms": daten["dauer_ms"], "modell_rohantworten": rohantworten, **vergleich}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    testdaten = REPO / "data" / "testdaten"
    parser.add_argument("--faelle", type=Path, nargs="+", default=[
        testdaten / "beratung_transfer.json", testdaten / "beratung_transfer_zusatz.json"])
    parser.add_argument("--projektstand", type=Path, default=REPO, help="Lokaler Checkout für den Vergleich")
    parser.add_argument("--bericht", type=Path)
    args = parser.parse_args()
    load_dotenv(REPO / ".env")
    sys.path.insert(0, str(args.projektstand.resolve()))
    from backend import app

    if app.KI_MOCK:
        parser.error("Für die Messung KI_MOCK=false setzen und die lokalen Modelldienste starten.")
    faelle = [fall for pfad in args.faelle for fall in json.loads(pfad.read_text(encoding="utf-8"))]
    jetzt = datetime.now().astimezone()
    ziel = args.bericht or BERICHTE / f"ticketberatung-{jetzt:%Y%m%d-%H%M%S-%f}.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bericht = {"beginn": jetzt.isoformat(), "faelle": []}
    with TemporaryDirectory(dir=ziel.parent) as temp, TestClient(app.app) as client:
        temp = Path(temp)
        # Die API erhält eine frische Arbeitskopie der Demo und einen separaten Fallindex.
        with patch.object(app, "LAUFZEIT_TICKETS", temp / "tickets.json"), \
                patch.object(app, "wissensbasis", app.rag.Wissensbasis(temp / "wissen.json")):
            status = client.get("/api/status?modelldetails=true").raise_for_status().json()
            if not status.get("ki_erreichbar") or not status.get("embedding_erreichbar") or status.get("beratung_erreichbar") is False:
                parser.error("Mindestens ein konfigurierter Modelldienst ist nicht erreichbar.")
            bericht["modelle"] = status
            for fall in faelle:
                ergebnis = pruefe_fall(client, app, fall)
                bericht["faelle"].append(ergebnis)
                ziel.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"{fall['id']} · {ergebnis['modus']} · {ergebnis['dauer_ms']} ms", flush=True)


if __name__ == "__main__":
    main()
