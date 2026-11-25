"""Misst die im Dashboard gespeicherte Priorität neuer Supporttickets mit echtem lokalem Modell."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dotenv import load_dotenv
from fastapi.testclient import TestClient


REPO = Path(__file__).resolve().parents[1]
STUFEN = ("niedrig", "mittel", "hoch", "sehr_hoch")


def pruefe_ticket(client, fall):
    eingang = {feld: fall[feld] for feld in ("kunde", "titel", "beschreibung")}
    ergebnis = {"id": fall["id"], **eingang, "soll": fall["erwartet"]["prioritaet"], "ist": None}
    ticket = client.post("/api/tickets", json=eingang).raise_for_status().json()
    antwort = client.post(f"/api/tickets/{ticket['id']}/analyse")
    ergebnis["http_status"] = antwort.status_code
    if antwort.is_error:
        return {**ergebnis, "fehler": antwort.text}
    daten = antwort.json()
    gespeichert = client.get(f"/api/tickets/{ticket['id']}").raise_for_status().json()
    if daten["modus"] != "llama" or not daten["gespeichert"]:
        raise ValueError("Die API lieferte keine gespeicherte Bewertung im echten Modellbetrieb.")
    ki = gespeichert["ki"]
    # --projektstand kann auch die frühere, gemischte Bewertung messen.
    quelle = ki.get("modus") or (ki.get("bewertungsquellen") or {}).get("prioritaet") or daten["modus"]
    return {**ergebnis, "ist": gespeichert["prioritaet"],
            "quelle": quelle, "kategorie": ki["kategorie"],
            "begruendung": ki["begruendung"], "dauer_ms": daten["dauer_ms"], "tokens": daten["tokens"]}


def kennzahlen(faelle):
    stufen = {stufe: {"richtig": 0, "gesamt": 0} for stufe in STUFEN}
    quellen = {}
    zu_hoch = zu_niedrig = ohne_bewertung = 0
    zeiten = []
    for fall in faelle:
        soll, ist = fall["soll"], fall["ist"]
        stufen[soll]["gesamt"] += 1
        if ist is None:
            ohne_bewertung += 1
            continue
        stufen[soll]["richtig"] += int(soll == ist)
        abstand = STUFEN.index(ist) - STUFEN.index(soll)
        zu_hoch += int(abstand > 0)
        zu_niedrig += int(abstand < 0)
        quelle = fall["quelle"]
        quellen[quelle] = quellen.get(quelle, 0) + 1
        zeiten.append(fall["dauer_ms"])
    return {"richtig": sum(stufe["richtig"] for stufe in stufen.values()), "gesamt": len(faelle),
            "je_stufe": stufen, "zu_hoch": zu_hoch, "zu_niedrig": zu_niedrig,
            "ohne_bewertung": ohne_bewertung, "quellen": quellen,
            "median_dauer_ms": median(zeiten) if zeiten else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--faelle", type=Path, required=True, help="Ticketliste mit erwartet.prioritaet")
    parser.add_argument("--bericht", type=Path, required=True, help="Neue JSON-Datei für den Lauf")
    parser.add_argument("--projektstand", type=Path, default=REPO, help="Checkout mit dem zu prüfenden Backend")
    args = parser.parse_args()
    projektstand = args.projektstand.resolve()
    if not (projektstand / "backend" / "app.py").is_file():
        parser.error("Unter --projektstand fehlt das Backend.")
    if args.bericht.exists():
        parser.error("Bitte einen neuen Dateinamen für den Bericht wählen.")
    load_dotenv(REPO / ".env")
    sys.path.insert(0, str(projektstand))
    from backend import app

    quelle = args.faelle.read_bytes()
    tickets = json.loads(quelle)
    faelle = [fall for fall in tickets if not fall["erwartet"].get("spam", False)]
    if not faelle or any(fall["erwartet"]["prioritaet"] not in STUFEN for fall in faelle):
        parser.error("Es werden Supporttickets mit gültiger Soll-Priorität benötigt.")
    if len({fall["id"] for fall in faelle}) != len(faelle):
        parser.error("Die Fallnummern müssen eindeutig sein.")

    args.bericht.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as temp, TestClient(app.app) as client, \
            patch.object(app, "LAUFZEIT_TICKETS", Path(temp) / "tickets.json"):
        status = client.get("/api/status?modelldetails=true").raise_for_status().json()
        dienst = "beratung_erreichbar" if status.get("support_mit_beratungsmodell") else "ki_erreichbar"
        if status["ki_modus"] != "llama" or not status.get(dienst):
            parser.error("Der lokale Klassifikationsdienst muss erreichbar sein und KI_MOCK=false gesetzt sein.")
        bericht = {"start": datetime.now().astimezone().isoformat(), "modell": status,
                   "daten_sha256": sha256(quelle).hexdigest(), "spam_ausgenommen": len(tickets) - len(faelle),
                   "backend_sha256": {p.name: sha256(p.read_bytes()).hexdigest()
                                      for p in sorted((projektstand / "backend").glob("*.py"))},
                   "faelle": []}
        for nummer, fall in enumerate(faelle, 1):
            bericht["faelle"].append(pruefe_ticket(client, fall))
            print(f"{nummer}/{len(faelle)} bearbeitet", flush=True)
    bericht.update(kennzahlen(bericht["faelle"]))
    with args.bericht.open("x", encoding="utf-8") as datei:
        json.dump(bericht, datei, ensure_ascii=False, indent=2)
        datei.write("\n")
    print(f"{bericht['richtig']}/{bericht['gesamt']} richtige Prioritäten. Bericht: {args.bericht}")


if __name__ == "__main__":
    main()
