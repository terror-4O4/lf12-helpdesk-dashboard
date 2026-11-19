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


def teste_modell(modell: str | None, tickets: list, erwartet: dict) -> dict:
    name = modell or "(einzelnes Modell)"
    print(f"\n=== {name} ===")
    try:
        ladezeit = lade_modell(modell)
    except HTTPException as fehler:
        print(f"  übersprungen: {fehler.detail}")
        return {"modell": name, "fehler": str(fehler.detail), "tickets": []}
    print(f"  geladen in {ladezeit:.1f} s")

    ergebnisse = []
    for i, t in enumerate(tickets, 1):
        soll = erwartet[t["id"]]
        start = time.perf_counter()
        try:
            ist, tokens = app.analysiere_llama(t)
            fehler = None
        except HTTPException as e:
            ist, tokens, fehler = None, None, str(e.detail)
        dauer = time.perf_counter() - start

        treffer = {f: ist is not None and ist[f] == soll[f] for f in FELDER}
        ergebnisse.append({
            "id": t["id"], "titel": t["titel"], "erwartet": {f: soll[f] for f in FELDER},
            "ki": ist, "treffer": treffer, "dauer_s": round(dauer, 2), "tokens": tokens,
            "fehler": fehler, "hinweis": soll.get("hinweis"),
        })
        status = "ok    " if all(treffer.values()) else "FEHLER"
        print(f"  [{i:2}/{len(tickets)}] #{t['id']} {status} {dauer:4.1f} s  {t['titel'][:50]}")

    return {"modell": name, "ladezeit_s": round(ladezeit, 1), "tickets": ergebnisse}


def kennzahlen(lauf: dict) -> dict:
    tk = lauf["tickets"]
    n = len(tk)
    je_feld = {f: sum(x["treffer"][f] for x in tk) for f in FELDER}
    dauer = [x["dauer_s"] for x in tk if x["fehler"] is None]
    return {
        "n": n,
        **je_feld,
        "gesamt": sum(je_feld.values()),
        "komplett": sum(all(x["treffer"].values()) for x in tk),
        "spam_uebersehen": sum(1 for x in tk if x["erwartet"]["spam"] and not (x["ki"] or {}).get("spam")),
        "spam_fehlalarm": sum(1 for x in tk if not x["erwartet"]["spam"] and (x["ki"] or {}).get("spam")),
        "dauer_avg": sum(dauer) / len(dauer) if dauer else 0,
        "dauer_max": max(dauer) if dauer else 0,
    }


def wert_text(feld: str, wert) -> str:
    if feld == "spam":
        return "Spam" if wert else "kein Spam"
    return str(wert)


def zahl(wert: float, stellen: int = 1) -> str:
    """Deutsche Schreibweise: 2,1 statt 2.1"""
    return f"{wert:.{stellen}f}".replace(".", ",")


def prozent(a: int, b: int) -> str:
    return f"{a}/{b} ({zahl(a / b * 100)} %)" if b else "-"


def als_markdown(laeufe: list, meta: dict) -> str:
    z = [f"# Auswertung Ticket-Analyse {meta['datum']}", "",
         f"- Tickets: {meta['tickets']}, erwartete Werte aus `data/testdaten/erwartet.json`",
         f"- llama-server: {meta['llama_url']}",
         f"- Analyse-Prompt (SHA-256, erste 12 Zeichen): `{meta['prompt_hash']}`", "",
         "| Modell | Priorität | Spam | Kategorie | Gesamt | Komplett richtig | Spam übersehen | Fehlalarme | Ø Dauer | Ladezeit |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for lauf in laeufe:
        if not lauf["tickets"]:
            z.append(f"| {lauf['modell']} | übersprungen: {lauf['fehler']} |||||||||")
            continue
        k = kennzahlen(lauf)
        n = k["n"]
        z.append(f"| {lauf['modell']} | {prozent(k['prioritaet'], n)} | {prozent(k['spam'], n)} | "
                 f"{prozent(k['kategorie'], n)} | **{prozent(k['gesamt'], 3 * n)}** | {k['komplett']}/{n} | "
                 f"{k['spam_uebersehen']} | {k['spam_fehlalarm']} | "
                 f"{zahl(k['dauer_avg'])} s | {zahl(lauf['ladezeit_s'], 0)} s |")

    for lauf in laeufe:
        falsch = [x for x in lauf["tickets"] if not all(x["treffer"].values())]
        if not lauf["tickets"]:
            continue
        z += ["", f"## Fehler {lauf['modell']} ({len(falsch)})", ""]
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
            z.append(f"| #{x['id']} {x['titel']} | {soll} | {ist} | {grund} | {x['hinweis'] or ''} |")
    return "\n".join(z) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Trefferquote der KI-Ticket-Analyse messen")
    parser.add_argument("-m", "--modell", action="append",
                        help="nur dieses Modell testen (mehrfach möglich), Standard: alle")
    args = parser.parse_args()

    tickets = app.lade_json(app.DATEN / "tickets.json")
    erwartet = {e["id"]: e for e in app.lade_json(app.DATEN / "erwartet.json")}
    fehlend = [t["id"] for t in tickets if t["id"] not in erwartet]
    if fehlend:
        sys.exit(f"Für diese Tickets fehlen erwartete Werte in erwartet.json: {fehlend}")

    standard = app.LLAMA_MODEL
    modelle = args.modell or verfuegbare_modelle()
    print(f"{len(tickets)} Tickets, {len(modelle)} Modell(e): "
          f"{', '.join(m or '(einzelnes Modell)' for m in modelle)}")

    laeufe = []
    try:
        for modell in modelle:
            laeufe.append(teste_modell(modell, tickets, erwartet))
    except KeyboardInterrupt:
        print("\nAbgebrochen, werte die bisherigen Ergebnisse aus.")
    finally:
        app.LLAMA_MODEL = standard

    if not laeufe:
        return
    meta = {
        "datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tickets": len(tickets),
        "llama_url": app.LLAMA_URL,
        "prompt_hash": hashlib.sha256(app.SYSTEMPROMPT_ANALYSE.encode()).hexdigest()[:12],
    }
    markdown = als_markdown(laeufe, meta)

    ZIEL.mkdir(parents=True, exist_ok=True)
    datei = ZIEL / f"auswertung-{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
    datei.with_suffix(".md").write_text(markdown, encoding="utf-8")
    datei.with_suffix(".json").write_text(
        json.dumps({"meta": meta, "laeufe": laeufe}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n" + markdown)
    print(f"Gespeichert: {datei.with_suffix('.md').relative_to(REPO)} und .json")


if __name__ == "__main__":
    main()
