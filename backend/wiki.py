"""Durchsucht eigene Fachnotizen zu fest verlinkten Wikipedia-Artikelfassungen."""

import json
import re
from functools import cache
from pathlib import Path


NOTIZEN = Path(__file__).resolve().parents[1] / "data" / "wissen" / "wikipedia.json"


@cache
def _artikel() -> list[dict]:
    return json.loads(NOTIZEN.read_text(encoding="utf-8"))


def _woerter(text: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", text.casefold()))


def suche(frage: str) -> list[dict]:
    """Findet ausdrücklich genannte Themen über Wörter und mehrteilige Begriffe."""
    anfrage = f" {_woerter(frage)} "
    treffer = []
    for artikel in _artikel():
        begriffe = [_woerter(b) for b in artikel["begriffe"]]
        passende = [b for b in begriffe if f" {b} " in anfrage]
        if passende:
            # Ein genauer Mehrwortbegriff steht vor einem allgemeineren Teilbegriff.
            laenge = max(len(b.split()) for b in passende)
            position = min(anfrage.index(f" {b} ") for b in passende)
            treffer.append((-laenge, position, artikel))

    ergebnis = []
    for _, _, artikel in sorted(treffer, key=lambda t: t[:2])[:2]:
        ergebnis.append({
            "titel": artikel["titel"], "text": artikel["text"], "url": artikel["url"],
            "quelle": f"Wikipedia · {artikel['artikel']}",
            "links": [{"titel": "Wikipedia-Artikel öffnen", "url": artikel["url"]}],
        })
    return ergebnis


def antwort(frage: str) -> tuple[str, list[dict]]:
    text = _woerter(frage)
    eintraege = suche(frage)
    if not eintraege:
        return "Dazu gibt es im lokalen Wikipedia-Bestand noch keine Fachnotiz.", []

    # Bei Betriebsfragen wäre eine bloße Begriffsdefinition eine irreführende Antwort.
    ist_begriff = any(text == _woerter(b) for a in _artikel() for b in a["begriffe"])
    begriffsfrage = re.search(
        r"\b(?:was (?:ist|sind|bedeutet|heißt|versteht man)|wofür (?:steht|braucht|ist)|"
        r"wie (?:funktioniert|funktionieren)|woran (?:erkenne|erkennt|kann)|"
        r"(?:erklär|erklaer)\w*|unterschied|definition|bedeutung|wozu)\b", text)
    kundendaten = re.search(
        r"\b(?:unser\w*|mein\w*|bei uns|bei mir)\b.{0,50}\b(?:adresse|serveradresse|passwort|"
        r"füllstand|speicherverbrauch|zugangsdat\w*)\b|"
        r"\b(?:adresse|passwort|füllstand|speicherverbrauch|zugangsdat\w*)\b.{0,30}"
        r"\b(?:unser\w*|mein\w*|bei uns|bei mir)\b", text)
    if kundendaten or not (ist_begriff or begriffsfrage):
        return ("Die lokalen Wikipedia-Artikel erklären IT-Begriffe. Für konkrete Werte oder "
                "Schritte in diesem Fall wähle die Ticketberatung oder die Kundendokumentation."), []
    return "\n\n".join(eintrag["text"] for eintrag in eintraege), eintraege
