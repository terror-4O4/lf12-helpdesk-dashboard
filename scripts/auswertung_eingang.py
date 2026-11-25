"""Prüft Regelhinweise und die KI-Einstufung der Demo über die lokale HTTP-API."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import httpx


REPO = Path(__file__).resolve().parent.parent
DATEN = REPO / "data" / "testdaten"
ZIEL = REPO / "data" / "laufzeit" / "auswertung"


def pruefe_ticket(client: httpx.Client, vorlage: dict, ticket: dict | None, soll: dict) -> dict:
    ergebnis = {"id": vorlage["id"], "soll": {k: soll[k] for k in ("spam", "kategorie", "prioritaet")}}
    if ticket is None or any(ticket.get(k) != vorlage[k] for k in ("kunde", "titel", "beschreibung")):
        return {**ergebnis, "ausgelassen": "Ticket fehlt oder hat abweichende Eingangsdaten."}
    ergebnis["regelhinweise"] = ticket["regelhinweise"]
    antwort = client.post(f"/api/tickets/{ticket['id']}/analyse", params={"speichern": "false"})
    ergebnis["http_status"] = antwort.status_code
    ergebnis["ablauf_ok"] = antwort.status_code == 200
    if ergebnis["ablauf_ok"]:
        ergebnis["bewertung"] = antwort.json()["ergebnis"]
    return ergebnis


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    vorlagen = json.loads((DATEN / "tickets.json").read_text(encoding="utf-8"))
    soll = {e["id"]: e for e in json.loads((DATEN / "erwartet.json").read_text(encoding="utf-8"))}
    faelle = []
    with httpx.Client(base_url=f"http://127.0.0.1:{args.port}", timeout=130, trust_env=False) as client:
        status = client.get("/api/status").raise_for_status().json()
        bestand = {t["id"]: t for t in client.get("/api/tickets").raise_for_status().json()}
        for vorlage in vorlagen:
            nummer = vorlage["id"]
            try:
                fall = pruefe_ticket(client, vorlage, bestand.get(nummer), soll[nummer])
            except (httpx.HTTPError, KeyError, ValueError, TypeError) as fehler:
                fall = {"id": nummer, "soll": soll[nummer], "fehler": str(fehler)}
            faelle.append(fall)

    geprueft = [f for f in faelle if "ausgelassen" not in f]
    spam = [f for f in geprueft if f["soll"]["spam"]]
    support = [f for f in geprueft if not f["soll"]["spam"]]
    zahlen = {
        "regelhinweis_bei_spam": [sum(bool(f.get("regelhinweise")) for f in spam), len(spam)],
        "regelhinweis_bei_support": [sum(bool(f.get("regelhinweise")) for f in support), len(support)],
        "ablauf_korrekt": [sum(f.get("ablauf_ok") is True for f in geprueft), len(geprueft)],
    }
    for feld in ("spam", "kategorie", "prioritaet"):
        zahlen[feld] = [sum(f.get("bewertung", {}).get(feld) == f["soll"][feld] for f in geprueft), len(geprueft)]

    datum = datetime.now()
    ZIEL.mkdir(parents=True, exist_ok=True)
    pfad = ZIEL / f"eingangspruefung-{datum:%Y-%m-%d_%H-%M-%S-%f}.json"
    bericht = {"datum": datum.isoformat(timespec="seconds"), "backend": status,
               "daten": "Demotickets mit unveränderter Eingangsnachricht",
               "ausgelassen": len(faelle) - len(geprueft), "kennzahlen": zahlen, "faelle": faelle}
    pfad.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Modus: {status['ki_modus']}. Geprüft: {len(geprueft)}/{len(faelle)} Demotickets.")
    for name, (richtig, anzahl) in zahlen.items():
        print(f"{name}: {richtig}/{anzahl}")
    print(pfad.relative_to(REPO))
    if not geprueft or any(not f.get("ablauf_ok") for f in geprueft):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
