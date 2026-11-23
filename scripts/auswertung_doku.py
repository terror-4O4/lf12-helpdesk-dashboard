"""Prüft die Kundendoku-Suche am laufenden lokalen Dashboard.

Aus dem Projektordner: python scripts/auswertung_doku.py
Das Protokoll landet unter data/laufzeit/auswertung/. Die Sollfälle bleiben unverändert.
"""

import argparse
import http.client
import json
import re
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATEN = REPO / "data" / "testdaten"
ZIEL = REPO / "data" / "laufzeit" / "auswertung"
URLS = re.compile(r"https?://[^\s<>()]+")
ZIELQUOTE = 0.8
KEINE_FUNDSTELLE = "In der ausgewählten Kundendokumentation gibt es keine passende Fundstelle."


def anfrage(port: int, timeout: float, pfad: str, daten: dict | None = None) -> dict:
    verbindung = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        if daten is None:
            verbindung.request("GET", pfad)
        else:
            verbindung.request("POST", pfad, json.dumps(daten), {"Content-Type": "application/json"})
        antwort = verbindung.getresponse()
        inhalt = antwort.read()
        if antwort.status != 200:
            raise ValueError(f"HTTP {antwort.status}: {inhalt.decode('utf-8', errors='replace')}")
        ergebnis = json.loads(inhalt)
        if not isinstance(ergebnis, dict):
            raise ValueError("JSON-Objekt erwartet.")
        return ergebnis
    finally:
        verbindung.close()


def pruefe_fall(fall: dict, ergebnis: dict) -> list[str]:
    fehler = []
    quellen = ergebnis["quellen"]
    antwort = ergebnis.get("antwort", "")
    if "ticket" in fall:
        if ergebnis["kunde"] != fall["kunde"]:
            fehler.append("Falscher Ticketkunde.")
    elif not antwort.strip():
        fehler.append("Leere Antwort.")

    soll = fall["quelle"]
    if soll is None:
        if quellen:
            fehler.append("Fundstellen trotz fehlender Dokumentation zum Fall.")
        if "frage" in fall and antwort.strip() != KEINE_FUNDSTELLE:
            fehler.append("Antwort muss den fehlenden Treffer kenntlich machen.")
    else:
        fund = next((q for q in quellen if q["quelle"] == soll), None)
        if not fund or fall["fundtext"].casefold() not in fund["text"].casefold():
            fehler.append("Erwartete Fundstelle oder Belegtext fehlt.")
        if "link" in fall and (not fund or fall["link"] not in {l["url"] for l in fund["links"]}):
            fehler.append("Hinterlegter Portal-Link fehlt an der Fundstelle.")

    kunde = fall["kunde"]
    if any(not q["quelle"].startswith(f"doku/{kunde}.md#") for q in quellen):
        fehler.append("Fundstelle stammt von einem anderen Kunden.")
    doku = (DATEN / "doku" / f"{kunde}.md").read_text(encoding="utf-8") if kunde else ""
    linkwerte = {l["url"] for q in quellen for l in q["links"]}
    linkwerte.update(URLS.findall(antwort))
    if linkwerte - set(URLS.findall(doku)):
        fehler.append("Antwort enthält einen Link außerhalb der hinterlegten Kundendoku.")

    erlaubt = fall.get("erlaubte_antwort")
    if erlaubt:
        zitate = [antwort, *(q["text"] for q in quellen)]
        if any(zitat.strip().removeprefix("- ") != erlaubt for zitat in zitate):
            fehler.append("Zugangsanfrage muss ausschließlich den hinterlegten Passwortmanager-Verweis liefern.")
    return fehler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000, help="Lokaler Backend-Port (Standard: 8000).")
    parser.add_argument("--timeout", type=float, default=150, help="Sekunden pro Anfrage (Standard: 150).")
    args = parser.parse_args()

    try:
        status = anfrage(args.port, min(5, args.timeout), "/api/status")
    except (OSError, http.client.HTTPException, ValueError) as fehler:
        parser.exit(2, f"Lokales Backend auf Port {args.port} nicht verwendbar: {fehler}\n")

    faelle = json.loads((DATEN / "fragen_doku.json").read_text(encoding="utf-8"))
    print(f"Kundendoku-Suche | Backend-Modus: {status.get('ki_modus', 'unbekannt')}")
    protokoll = []
    for fall in faelle:
        gruppe = "Ticketbezug" if "ticket" in fall else "Fundstelle" if fall["quelle"] else "Kein Treffer"
        r = {}
        try:
            if "ticket" in fall:
                r = anfrage(args.port, args.timeout, f"/api/tickets/{fall['ticket']}/doku")
            else:
                r = anfrage(args.port, args.timeout, f"/api/kunden/{fall['kunde']}/doku/suche",
                            {"frage": fall["frage"]})
            fehler = pruefe_fall(fall, r)
        except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError, AttributeError) as exc:
            fehler = [f"Fehler bei Anfrage oder Antwort: {exc}"]
        protokoll.append({"gruppe": gruppe, "fall": fall, "ergebnis": r, "fehler": fehler})
        print(f"  {fall['id']}  {'OK' if not fehler else 'FEHLER  ' + ' '.join(fehler)}")

    gesamt_ok = True
    for gruppe, ziel in (("Fundstelle", ZIELQUOTE), ("Kein Treffer", 1.0), ("Ticketbezug", 1.0)):
        geprueft = [eintrag for eintrag in protokoll if eintrag["gruppe"] == gruppe]
        ok = sum(not eintrag["fehler"] for eintrag in geprueft)
        quote = ok / len(geprueft) if geprueft else 0.0
        gesamt_ok &= quote >= ziel
        print(f"{gruppe}: {ok}/{len(geprueft)} ({quote:.0%}), Ziel {ziel:.0%}")

    # Ein fehlender Passwortmanager-Verweis darf nicht von der Trefferquote verdeckt werden.
    gesamt_ok &= all(not eintrag["fehler"] for eintrag in protokoll if "erlaubte_antwort" in eintrag["fall"])
    ZIEL.mkdir(parents=True, exist_ok=True)
    datum = datetime.now()
    protokolldatei = ZIEL / f"doku-{datum:%Y-%m-%d_%H-%M-%S}.json"
    report = {"datum": datum.isoformat(timespec="seconds"), "backend_modus": status.get("ki_modus"),
              "chat_modell": status.get("ki_modell"),
              "bestanden": gesamt_ok, "faelle": protokoll}
    protokolldatei.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Testprotokoll: {protokolldatei.relative_to(REPO)}")
    return 0 if gesamt_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
