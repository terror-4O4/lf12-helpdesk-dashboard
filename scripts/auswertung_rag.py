"""Misst die Lösungsvorschläge aus ähnlichen Tickets (RAG) gegen die Messziele.

Messziele laut Projektantrag V2.1:
  1. Gibt es zu einem Testticket ein ähnliches gelöstes Ticket, soll es in
     mindestens 80 % der Fälle unter den ersten drei Vorschlägen erscheinen.
  2. Gibt es keinen ähnlichen Fall, soll die KI in mindestens 80 % der Fälle
     nichts erfinden, sondern das kenntlich machen.

Welches gelöste Ticket passt, steht im Feld "aehnlich" in
data/testdaten/erwartet.json ([] = kein passender Fall, null = nicht Teil des Tests).

Zusätzlich:
  - Ähnlichkeitswerte aller Fälle und eine Empfehlung für RAG_SCHWELLE
  - Prüfung "Wissensbasis wächst": ein frisch geschlossenes Ticket wird beim
    nächsten ähnlichen Fall gefunden
  - mit --vergleich: Lösungsvorschlag OHNE Ticket-Historie (nur das Modell)
    gegen MIT Ticket-Historie, für das Testprotokoll

Benutzt die Testdaten (nicht die Arbeitskopie) und eine eigene Vektor-Datei,
das Dashboard wird also nicht verändert.

Aufruf aus dem Repo-Hauptordner mit aktivierter .venv:
    python scripts/auswertung_rag.py                 Suche und KI-Vorschläge
    python scripts/auswertung_rag.py --nur-suche     nur Suche, ohne Chat-KI (schnell)
    python scripts/auswertung_rag.py --vergleich     zusätzlich ohne/mit Historie

Ergebnis in der Konsole sowie als Markdown und JSON unter data/laufzeit/auswertung/.
"""

import argparse
import copy
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from fastapi import HTTPException  # noqa: E402

import backend.app as app  # noqa: E402  (liest .env, prüft "nur lokale Adressen")
from backend import rag  # noqa: E402

ZIEL = REPO / "data" / "laufzeit" / "auswertung"
DATEN = REPO / "data" / "testdaten"
ZIELWERT = 0.8


def lade_testdaten():
    tickets = json.loads((DATEN / "tickets.json").read_text(encoding="utf-8"))
    erwartet = {e["id"]: e for e in json.loads((DATEN / "erwartet.json").read_text(encoding="utf-8"))}
    tests = [t for t in tickets if erwartet.get(t["id"], {}).get("aehnlich") is not None]
    return tickets, erwartet, tests


def prozent(a: int, b: int) -> str:
    return f"{a}/{b} = {a / b:.0%}" if b else "–"


def empfehle_schwelle(zeilen: list[dict]) -> tuple[float, int]:
    """Schwelle, bei der die Suche allein die meisten Testfälle richtig hat.

    Richtig heißt: passender Fall über der Schwelle und unter den Top 3, bzw.
    bei "kein Fall" liegt nichts über der Schwelle. Die Chat-KI kann danach
    noch unpassende Fälle verwerfen, das ist hier nicht eingerechnet.
    """
    beste, beste_punkte = app.aktuelle_schwelle(), -1
    for schritt in range(20, 91):
        s = schritt / 100
        punkte = 0
        for z in zeilen:
            ueber = [x for x in z["alle"] if x["wert"] >= s][:3]
            if z["erwartet"]:
                punkte += any(x["id"] in z["erwartet"] for x in ueber)
            else:
                punkte += not ueber
        if punkte > beste_punkte:
            beste, beste_punkte = s, punkte
    return beste, beste_punkte


def vorschlag_ohne_historie(t: dict) -> tuple[str, float]:
    """Gleiche Frage an das Modell, aber ohne gelöste Tickets (für den Vergleich)."""
    start = time.perf_counter()
    text, _ = app.frage_llama([
        {"role": "system", "content": app.SYSTEMPROMPT_FRAGE},
        {"role": "user", "content": f"Nenne bis zu drei mögliche Ursachen mit Lösungsweg für dieses Ticket:\n"
                                    f"{t['titel']}. {t['beschreibung']}"},
    ], temperatur=0)
    return text, time.perf_counter() - start


def pruefe_wachstum(tickets: list, wb: rag.Wissensbasis) -> dict:
    """Schließt #1022 (Outlook, Add-In) im Speicher und sucht für ein neues,
    anders formuliertes Ticket. Erwartet: #1022 steht unter den Top 3."""
    liste = copy.deepcopy(tickets)
    t1022 = next(t for t in liste if t["id"] == 1022)
    t1022.update(status="geschlossen", ursache="Outlook-Add-In nach Update des Bauzeiten-Programms",
                 loesungsweg="Add-In unter Datei > Optionen > Add-Ins deaktiviert, Outlook startet wieder.")
    neu = {"id": 99999, "kunde": "bau", "titel": "Mail-Programm geht direkt wieder zu",
           "beschreibung": "Bei unserer Bauleiterin geht das Mailprogramm nach dem Öffnen gleich wieder "
                           "zu. Seit gestern das Update vom Bauzeiten-Programm drauf ist."}
    treffer, _ = app.finde_aehnliche(neu, liste, wb=wb)
    ids = [x["id"] for x in treffer]
    return {"gefunden": 1022 in ids, "top3": treffer}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nur-suche", action="store_true", help="ohne Chat-KI, nur die Suche messen")
    parser.add_argument("--vergleich", action="store_true", help="zusätzlich Vorschläge ohne Ticket-Historie")
    args = parser.parse_args()

    tickets, erwartet, tests = lade_testdaten()
    ZIEL.mkdir(parents=True, exist_ok=True)
    wb = rag.Wissensbasis(ZIEL / "wissensbasis-test.json")
    faelle = [t for t in tickets if rag.ist_fall(t)]

    print(f"Modus: {'Mock' if app.KI_MOCK else 'llama'} | Embeddings: {app.EMBED_URL} | "
          f"Chat: {app.LLAMA_URL} {app.LLAMA_MODEL}")
    print(f"Wissensbasis: {len(faelle)} gelöste Tickets | Schwelle {app.aktuelle_schwelle()} | "
          f"Kundenbonus {app.RAG_KUNDENBONUS}")
    print(f"Testtickets: {len(tests)} ({sum(bool(erwartet[t['id']]['aehnlich']) for t in tests)} mit passendem Fall)\n")

    start = time.perf_counter()
    try:
        app.finde_aehnliche(tests[0], tickets, wb=wb)  # Wissensbasis einmal aufbauen
    except HTTPException as fehler:
        sys.exit(f"Suche nicht möglich: {fehler.detail}")
    aufbau = time.perf_counter() - start
    print(f"Wissensbasis aufgebaut in {aufbau:.1f} s\n")

    zeilen = []
    for i, t in enumerate(tests, 1):
        soll = erwartet[t["id"]]["aehnlich"]
        alle, _ = app.finde_aehnliche(t, tickets, anzahl=len(faelle), schwelle=-1.0, wb=wb)
        z = {"id": t["id"], "titel": t["titel"], "erwartet": soll, "alle": alle,
             "hinweis": erwartet[t["id"]].get("aehnlich_hinweis")}

        if args.nur_suche:
            top3 = [x for x in alle if x["wert"] >= app.aktuelle_schwelle()][:3]
            z.update(top3=[x["id"] for x in top3], passender_fall=bool(top3), ki_tickets=[x["id"] for x in top3],
                     dauer_s=None, tokens=None, fehler=None)
        else:
            try:
                v = app.erzeuge_vorschlag(t, tickets, wb=wb)
                e = v["ergebnis"]
                z.update(top3=[x["id"] for x in v["treffer"]], passender_fall=e["passender_fall"],
                         ki_tickets=sorted({n for s in e["vorschlaege"] for n in s["tickets"]}),
                         vorschlaege=e["vorschlaege"], ki_hinweis=e["hinweis"], modus=v["modus"],
                         dauer_s=round(v["dauer_ms"] / 1000, 2), dauer_suche_ms=v["dauer_suche_ms"],
                         tokens=v["tokens"], fehler=None)
            except HTTPException as fehler:
                z.update(top3=[], passender_fall=None, ki_tickets=[], dauer_s=None, tokens=None,
                         fehler=str(fehler.detail))

        if soll:
            z["suche_ok"] = any(x in soll for x in z["top3"])
            z["ki_ok"] = bool(z["passender_fall"]) and any(x in soll for x in z["ki_tickets"])
        else:
            z["suche_ok"] = not z["top3"]
            z["ki_ok"] = z["passender_fall"] is False

        if args.vergleich and soll and not app.KI_MOCK:
            z["ohne_historie"], z["ohne_historie_s"] = vorschlag_ohne_historie(t)

        zeilen.append(z)
        bester = alle[0] if alle else {"id": "-", "wert": 0}
        status = "ok    " if z["ki_ok"] else "FEHLER"
        soll_text = ", ".join(f"#{x}" for x in soll) or "kein Fall"
        ki_text = ", ".join(f"#{x}" for x in z["ki_tickets"]) if z["passender_fall"] else "kein Fall"
        print(f"  [{i:2}/{len(tests)}] #{t['id']} {status} erwartet {soll_text:<9} "
              f"KI {ki_text:<18} "
              f"(bester #{bester['id']} {bester['wert']:.2f})  {t['titel'][:40]}")
        if z.get("fehler"):
            print(f"         Fehler: {z['fehler']}")

    mit = [z for z in zeilen if z["erwartet"]]
    ohne = [z for z in zeilen if not z["erwartet"]]
    m1_suche = sum(z["suche_ok"] for z in mit)
    m1_ki = sum(z["ki_ok"] for z in mit)
    m2 = sum(z["ki_ok"] for z in ohne)
    schwelle, punkte = empfehle_schwelle(zeilen)
    wachstum = pruefe_wachstum(tickets, wb)
    dauer = [z["dauer_s"] for z in zeilen if z.get("dauer_s") is not None]

    def bewertung(a, b):
        return "erreicht" if b and a / b >= ZIELWERT else "verfehlt"

    zusammenfassung = [
        f"Messziel 1, passender Fall unter den Top 3 (Suche): {prozent(m1_suche, len(mit))}",
        f"Messziel 1, KI verweist auf den passenden Fall:       {prozent(m1_ki, len(mit))} ({bewertung(m1_ki, len(mit))})",
        f"Messziel 2, ohne passenden Fall nichts erfunden:      {prozent(m2, len(ohne))} ({bewertung(m2, len(ohne))})",
        f"Wissensbasis wächst (#1022 nach Schließen gefunden):   {'ja' if wachstum['gefunden'] else 'NEIN'}",
        f"Empfohlene RAG_SCHWELLE (nur Suche): {schwelle:.2f} ({punkte}/{len(zeilen)} Testfälle richtig), "
        f"eingestellt: {app.aktuelle_schwelle()}",
    ]
    if dauer:
        zusammenfassung.append(f"Dauer je Ticket: Ø {sum(dauer) / len(dauer):.1f} s, max. {max(dauer):.1f} s")
    print("\n" + "\n".join(zusammenfassung))

    # --- Speichern ---------------------------------------------------------------
    stempel = datetime.now().strftime("%Y-%m-%d_%H%M")
    lauf = {"zeit": stempel, "modus": "mock" if app.KI_MOCK else "llama", "chat_modell": app.LLAMA_MODEL,
            "embedding": app.einbetter.kennung, "schwelle": app.aktuelle_schwelle(),
            "kundenbonus": app.RAG_KUNDENBONUS, "nur_suche": args.nur_suche,
            "aufbau_s": round(aufbau, 2), "zusammenfassung": zusammenfassung,
            "wachstum": wachstum, "tickets": zeilen}
    (ZIEL / f"rag_{stempel}.json").write_text(json.dumps(lauf, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# RAG-Auswertung {stempel}", "",
          f"- Modus: {lauf['modus']}, Chat-Modell: {app.LLAMA_MODEL or '-'}, Embeddings: {app.einbetter.kennung}",
          f"- Wissensbasis: {len(faelle)} gelöste Tickets, Aufbau {aufbau:.1f} s",
          f"- Schwelle {app.aktuelle_schwelle()}, Kundenbonus {app.RAG_KUNDENBONUS}", "",
          *[f"- {s}" for s in zusammenfassung], "",
          "| Ticket | Erwartet | Top 3 (Suche) | KI verweist auf | Bester Wert | Ergebnis | Dauer |",
          "|---|---|---|---|---|---|---|"]
    for z in zeilen:
        bester = z["alle"][0] if z["alle"] else {"id": "-", "wert": 0}
        md.append(f"| #{z['id']} {z['titel']} | {', '.join(f'#{x}' for x in z['erwartet']) or 'kein Fall'} | "
                  f"{', '.join(f'#{x}' for x in z['top3']) or '–'} | "
                  f"{', '.join(f'#{x}' for x in z['ki_tickets']) if z['passender_fall'] else 'kein Fall'} | "
                  f"#{bester['id']} {bester['wert']:.2f} | {'ok' if z['ki_ok'] else 'Fehler'} | "
                  f"{z['dauer_s'] if z.get('dauer_s') is not None else '–'} s |")
    if args.vergleich and not app.KI_MOCK:
        md += ["", "## Vergleich ohne und mit Ticket-Historie", ""]
        for z in mit:
            md += [f"### #{z['id']} {z['titel']}", "", f"**Ohne Historie** ({z.get('ohne_historie_s', 0):.1f} s):", "",
                   z.get("ohne_historie", "–"), "", f"**Mit Historie** ({z.get('dauer_s') or 0} s):", ""]
            md += [f"{n}. {v['ursache']}: {v['loesungsweg']} (#{', #'.join(map(str, v['tickets']))})"
                   for n, v in enumerate(z.get("vorschlaege", []), 1)] or ["kein Fall"]
            md.append("")
    (ZIEL / f"rag_{stempel}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nGespeichert: data/laufzeit/auswertung/rag_{stempel}.md und .json")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nAbgebrochen.")
