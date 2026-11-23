"""Misst, wie gut die KI die Testtickets bewertet (Trefferquote, Dauer).

Lässt alle Tickets aus data/testdaten/tickets.json von der KI analysieren und
vergleicht das Ergebnis mit data/testdaten/erwartet.json. Benutzt dafür genau
die Prompts und Prüfungen des Backends, getestet wird also das, was später im
Dashboard läuft. Die Testdaten und die Arbeitskopie werden nicht verändert.

Läuft der llama-server im Router-Modus (Dienst auf dem Mac Pro), werden
nacheinander alle Modelle getestet, die der Server anbietet. Das Modell aus
LLAMA_MODEL kommt zuletzt dran, damit es danach wieder geladen ist.

Aufruf aus dem Repo-Hauptordner mit aktivierter .venv:
    python scripts/auswertung.py                         alle Modelle
    python scripts/auswertung.py -m gemma-4-12b-it-qat-q4_0   nur dieses Modell
    python scripts/auswertung.py -m modell_a -m modell_b      mehrere Modelle
    python scripts/auswertung.py --vergleich           beide Prompts auf neuen Testtickets
    python scripts/auswertung.py --vergleich --mock    Probelauf mit Platzhalter-Klassifikator

Ergebnis: Tabelle in der Konsole und als Markdown (für das Testprotokoll) und
JSON unter data/laufzeit/auswertung/ (nicht im Repo).
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import backend.app as app  # noqa: E402  (liest .env, prüft "nur lokale KI-Adresse")

FELDER = ("prioritaet", "spam", "kategorie")
ZIEL = REPO / "data" / "laufzeit" / "auswertung"
VERGLEICHSDATEN = "tickets_promptvergleich.json"
PROMPTS = {"einfach": app.SYSTEMPROMPT_ANALYSE_EINFACH, "angepasst": app.SYSTEMPROMPT_ANALYSE}


def kopfzeilen() -> dict:
    return {"Authorization": f"Bearer {app.LLAMA_API_KEY}"} if app.LLAMA_API_KEY else {}


def verfuegbare_modelle() -> list[str | None]:
    """Modelle des llama-servers. [None] = Server läuft mit genau einem Modell."""
    try:
        r = httpx.get(f"{app.LLAMA_URL}/models", headers=kopfzeilen(), timeout=10, trust_env=False)
    except httpx.HTTPError as fehler:
        sys.exit(f"llama-server nicht erreichbar unter {app.LLAMA_URL}: {fehler}")
    if r.status_code == 401:
        sys.exit("llama-server lehnt ab (401): LLAMA_API_KEY in der .env fehlt oder ist falsch.")
    if r.status_code != 200 or "data" not in r.json():
        return [None]
    ids = sorted(m["id"] for m in r.json()["data"])
    # Das eingestellte Modell zuletzt, damit es nach der Auswertung geladen bleibt
    if app.LLAMA_MODEL in ids:
        ids.remove(app.LLAMA_MODEL)
        ids.append(app.LLAMA_MODEL)
    return ids


def lade_modell(modell: str | None) -> float:
    """Schickt eine kurze Anfrage, damit das Modell geladen ist. Gibt die Ladezeit zurück."""
    app.LLAMA_MODEL = modell or ""
    start = time.perf_counter()
    app.frage_llama([{"role": "user", "content": "Antworte nur mit OK."}], temperatur=0)
    return time.perf_counter() - start


def bewerte_ticket(t: dict, soll: dict, prompt: str, mock: bool) -> dict:
    messung = {}
    start = time.perf_counter()
    try:
        if mock:
            ist, tokens = app.analysiere_mock(t), None
        else:
            ist, tokens = app.analysiere_llama(t, systemprompt=prompt, messung=messung)
        fehler = None
    except HTTPException as e:
        ist, tokens, fehler = None, None, str(e.detail)
    return {
        "id": t["id"], "titel": t["titel"], "erwartet": {f: soll[f] for f in FELDER},
        "ki": ist,
        "treffer": {f: ist is not None and ist[f] == soll[f] for f in FELDER},
        "dauer_s": None if mock else round(time.perf_counter() - start, 3),
        "tokens": tokens, "fehler": fehler, "hinweis": soll.get("hinweis"),
        "zeit_bis_erster_token_s": messung.get("zeit_bis_erster_token_s"),
        "antwortzeit_s": messung.get("antwortzeit_s"),
        "tokens_pro_s": messung.get("tokens_pro_s"),
    }


def teste_modell(modell: str | None, tickets: list, erwartet: dict, varianten: list[str],
                 mock: bool = False) -> list[dict]:
    name = "Mock (Platzhalter)" if mock else modell or "(Server-Standardmodell)"
    print(f"\n=== {name} ===")
    laeufe = [{"modell": name, "variante": v, "tickets": []} for v in varianten]
    if not mock:
        try:
            ladezeit = lade_modell(modell)
        except HTTPException as fehler:
            print(f"  übersprungen: {fehler.detail}")
            return [dict(lauf, fehler=str(fehler.detail)) for lauf in laeufe]
        print(f"  Modellantwort zur Aufwärmanfrage nach {ladezeit:.1f} s")
        for lauf in laeufe:
            lauf["ladezeit_s"] = round(ladezeit, 3)

    for i, t in enumerate(tickets, 1):
        soll = erwartet[t["id"]]
        # Die wechselnde Reihenfolge verteilt Effekte durch Aufwärmen und Prompt-Cache.
        reihenfolge = laeufe if i % 2 else reversed(laeufe)
        for lauf in reihenfolge:
            variante = lauf["variante"]
            ergebnis = bewerte_ticket(t, soll, PROMPTS[variante], mock)
            lauf["tickets"].append(ergebnis)
            status = "ok" if all(ergebnis["treffer"].values()) else "FEHLER"
            dauer = messwert(ergebnis["dauer_s"], "s")
            print(f"  [{i:2}/{len(tickets)}] #{t['id']} {variante:<9} {status:<6} {dauer}  {t['titel'][:50]}")
    return laeufe


def kennzahlen(lauf: dict) -> dict:
    tk = lauf["tickets"]
    n = len(tk)
    je_feld = {f: sum(x["treffer"][f] for x in tk) for f in FELDER}
    messfelder = ("dauer_s", "zeit_bis_erster_token_s", "antwortzeit_s", "tokens_pro_s")
    messwerte = {
        feld: [x[feld] for x in tk if x["fehler"] is None and x.get(feld) is not None]
        for feld in messfelder
    }
    return {
        "n": n,
        **je_feld,
        "gesamt": sum(je_feld.values()),
        "komplett": sum(all(x["treffer"].values()) for x in tk),
        "spam_uebersehen": sum(1 for x in tk if x["erwartet"]["spam"] and not (x["ki"] or {}).get("spam")),
        "spam_fehlalarm": sum(1 for x in tk if not x["erwartet"]["spam"] and (x["ki"] or {}).get("spam")),
        "dauer_avg": sum(messwerte["dauer_s"]) / len(messwerte["dauer_s"]) if messwerte["dauer_s"] else None,
        "dauer_max": max(messwerte["dauer_s"], default=None),
        "mittelwerte": {feld: sum(werte) / len(werte) if werte else None
                         for feld, werte in messwerte.items()},
        "anzahl_messwerte": {feld: len(werte) for feld, werte in messwerte.items()},
    }


def wert_text(feld: str, wert) -> str:
    if feld == "spam":
        return "Spam" if wert else "kein Spam"
    return str(wert)


def zahl(wert: float, stellen: int = 1) -> str:
    """Deutsche Schreibweise: 2,1 statt 2.1"""
    return f"{wert:.{stellen}f}".replace(".", ",")


def messwert(wert: float | None, einheit: str) -> str:
    return "–" if wert is None else f"{zahl(wert, 3 if einheit == 's' else 1)} {einheit}"


def prozent(a: int, b: int) -> str:
    return f"{a}/{b} ({zahl(a / b * 100)} %)" if b else "-"


def tabellenzelle(text: str) -> str:
    return " ".join(text.splitlines()).replace("|", r"\|")


def als_markdown(laeufe: list, meta: dict) -> str:
    prompts = ", ".join(f"{name} `{hashwert}`" for name, hashwert in meta["prompts"].items())
    z = [f"# Auswertung Ticket-Analyse {meta['datum']}", "",
         f"- Tickets: {meta['tickets']}, Testdaten: {meta['datenbasis']}",
         f"- Modus: {meta['modus']}",
         f"- Prompts (SHA-256, erste 12 Zeichen): {prompts}", ""]
    if meta["modus"] == "mock":
        z += ["Mock-Probelauf mit festem Platzhalter-Klassifikator. Die Simulation nutzt keinen Prompt.",
              "Die Werte sind kein Nachweis für Modellgüte oder Modellleistung.", ""]
    else:
        z += [f"- llama-server: {meta['llama_url']}", ""]
    z += ["| Modell | Prompt | Priorität | Spam | Kategorie | Gesamt | Komplett | Spam übersehen | Fehlalarme |",
          "|---|---|---|---|---|---|---|---|---|"]
    for lauf in laeufe:
        if not lauf["tickets"]:
            z.append(f"| {lauf['modell']} | {lauf['variante']} | übersprungen: {lauf['fehler']} ||||||")
            continue
        k = lauf["kennzahlen"]
        n = k["n"]
        z.append(f"| {lauf['modell']} | {lauf['variante']} | {prozent(k['prioritaet'], n)} | {prozent(k['spam'], n)} | "
                 f"{prozent(k['kategorie'], n)} | **{prozent(k['gesamt'], 3 * n)}** | {k['komplett']}/{n} | "
                 f"{k['spam_uebersehen']} | {k['spam_fehlalarm']} |")

    z += ["", "| Modell | Prompt | Ø Erster Token | Ø Antwort vollständig | Ø Token pro Sekunde | Ø Gesamt | Aufwärmanfrage |",
          "|---|---|---|---|---|---|---|"]
    for lauf in laeufe:
        if not lauf["tickets"]:
            continue
        k = lauf["kennzahlen"]["mittelwerte"]
        z.append(f"| {lauf['modell']} | {lauf['variante']} | {messwert(k['zeit_bis_erster_token_s'], 's')} | "
                 f"{messwert(k['antwortzeit_s'], 's')} | {messwert(k['tokens_pro_s'], 'Tok/s')} | "
                 f"{messwert(k['dauer_s'], 's')} | {messwert(lauf.get('ladezeit_s'), 's')} |")

    for lauf in laeufe:
        falsch = [x for x in lauf["tickets"] if not all(x["treffer"].values())]
        if not lauf["tickets"]:
            continue
        z += ["", f"## Fehler {lauf['modell']} mit Prompt {lauf['variante']} ({len(falsch)})", ""]
        if not falsch:
            z.append("Keine Fehler.")
            continue
        z += ["| Ticket | Erwartet | KI | Begründung der KI | Hinweis Testdaten |", "|---|---|---|---|---|"]
        for x in falsch:
            soll = ", ".join(wert_text(f, x["erwartet"][f]) for f in FELDER)
            if x["ki"] is None:
                ist, grund = "Fehler", x["fehler"]
            else:
                ist = ", ".join(f"**{wert_text(f, x['ki'][f])}**" if not x["treffer"][f]
                                else wert_text(f, x["ki"][f]) for f in FELDER)
                grund = x["ki"].get("begruendung", "")
            z.append(f"| #{x['id']} {tabellenzelle(x['titel'])} | {soll} | {ist} | "
                     f"{tabellenzelle(grund)} | {tabellenzelle(x['hinweis'] or '')} |")
    if meta["vergleich"]:
        z += ["", "## Priorität je Testticket", "",
              "| Modell | Prompt | Ticket | Soll | Modellantwort | Erster Token | Antwort vollständig | Token pro Sekunde |",
              "|---|---|---|---|---|---|---|---|"]
        for lauf in laeufe:
            for ticket in lauf["tickets"]:
                ist = ticket["ki"]["prioritaet"] if ticket["ki"] else "Fehler"
                z.append(f"| {lauf['modell']} | {lauf['variante']} | #{ticket['id']} | "
                         f"{ticket['erwartet']['prioritaet']} | {ist} | "
                         f"{messwert(ticket['zeit_bis_erster_token_s'], 's')} | "
                         f"{messwert(ticket['antwortzeit_s'], 's')} | {messwert(ticket['tokens_pro_s'], 'Tok/s')} |")
    return "\n".join(z) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Trefferquote der KI-Ticket-Analyse messen")
    parser.add_argument("-m", "--modell", action="append",
                        help="nur dieses Modell testen (mehrfach möglich), Standard: alle")
    parser.add_argument("--vergleich", action="store_true",
                        help="einfachen und angepassten Prompt auf zurückgehaltenen Tickets vergleichen")
    parser.add_argument("--mock", action="store_true",
                        help="Auswertung offline mit Platzhalter testen. Keine Modellmessung.")
    args = parser.parse_args()

    if args.mock and args.modell:
        parser.error("--mock kann kein Modell testen")

    if args.vergleich:
        tickets = app.lade_json(app.DATEN / VERGLEICHSDATEN)
        erwartet = {t["id"]: {**t["erwartet"], "hinweis": t.get("hinweis")} for t in tickets}
        varianten = list(PROMPTS)
        datenbasis = f"`data/testdaten/{VERGLEICHSDATEN}`"
    else:
        tickets = app.lade_json(app.DATEN / "tickets.json")
        erwartet = {e["id"]: e for e in app.lade_json(app.DATEN / "erwartet.json")}
        fehlend = [t["id"] for t in tickets if t["id"] not in erwartet]
        if fehlend:
            sys.exit(f"Für diese Tickets fehlen erwartete Werte in erwartet.json: {fehlend}")
        varianten = ["angepasst"]
        datenbasis = "`data/testdaten/tickets.json` und `data/testdaten/erwartet.json`"

    standard = app.LLAMA_MODEL
    if args.mock:
        modelle = [None]
    elif args.vergleich:
        modelle = args.modell or [standard or None]
    else:
        modelle = args.modell or verfuegbare_modelle()
    print(f"{len(tickets)} Tickets, {len(modelle)} Modell(e): "
          f"{'Mock (Platzhalter)' if args.mock else ', '.join(m or '(Server-Standardmodell)' for m in modelle)}")

    laeufe = []
    try:
        for modell in modelle:
            laeufe.extend(teste_modell(modell, tickets, erwartet, varianten, mock=args.mock))
    except KeyboardInterrupt:
        print("\nAbgebrochen, werte die bisherigen Ergebnisse aus.")
    finally:
        app.LLAMA_MODEL = standard

    if not laeufe:
        return
    for lauf in laeufe:
        lauf["kennzahlen"] = kennzahlen(lauf)
    meta = {
        "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tickets": len(tickets),
        "datenbasis": datenbasis,
        "modus": "mock" if args.mock else "llama",
        "vergleich": args.vergleich,
        "llama_url": None if args.mock else app.LLAMA_URL,
        "prompt_hash": hashlib.sha256(app.SYSTEMPROMPT_ANALYSE.encode()).hexdigest()[:12],
        "prompts": {v: hashlib.sha256(PROMPTS[v].encode()).hexdigest()[:12] for v in varianten},
    }
    markdown = als_markdown(laeufe, meta)

    ZIEL.mkdir(parents=True, exist_ok=True)
    praefix = "promptvergleich" if args.vergleich else "auswertung"
    datei = ZIEL / f"{praefix}-{meta['modus']}-{datetime.now():%Y-%m-%d_%H-%M-%S-%f}"
    datei.with_suffix(".md").write_text(markdown, encoding="utf-8")
    datei.with_suffix(".json").write_text(
        json.dumps({"meta": meta, "laeufe": laeufe}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n" + markdown)
    print(f"Gespeichert: {datei.with_suffix('.md').relative_to(REPO)} und .json")


if __name__ == "__main__":
    main()
