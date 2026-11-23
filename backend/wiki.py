"""Lokale Fachnotizen und getrennt belegte Prüfschritte für die Ticketberatung."""

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


def _enthaelt(text: str, begriff: str) -> bool:
    return f" {_woerter(begriff)} " in text


def _symptom_passt(text: str, gruppen: list[list[str]]) -> bool:
    # Ein Thema und ein zugehöriges Symptom müssen gemeinsam vorkommen.
    return bool(gruppen) and all(any(_enthaelt(text, wort) for wort in alternativen)
                                 for alternativen in gruppen)


def _finde(meldung: str, frage: str, mit_diagnose: bool) -> list[dict]:
    fokus = f" {_woerter(frage)} "
    gesamt = f"{fokus} {_woerter(meldung)} "
    treffer = []
    for artikel in _artikel():
        begriffe = [b for b in artikel["begriffe"] if _enthaelt(gesamt, b)]
        symptome = artikel.get("symptome", [])
        hat_symptom = mit_diagnose and _symptom_passt(gesamt, symptome)
        if not (begriffe or hat_symptom):
            continue
        staerke = max((len(_woerter(b).split()) for b in begriffe), default=0)
        if hat_symptom:
            staerke = max(staerke, len(symptome))
        im_fokus = any(_enthaelt(fokus, b) for b in begriffe) or (
            hat_symptom and _symptom_passt(fokus, symptome))
        position = min((gesamt.index(f" {_woerter(b)} ") for b in begriffe), default=len(gesamt))
        treffer.append(((not im_fokus, -staerke, position), artikel))

    ergebnis = []
    for _, artikel in sorted(treffer, key=lambda t: t[0])[:2]:
        quelle = {
            "titel": artikel["titel"], "text": artikel["text"], "url": artikel["url"],
            "quelle": f"Wikipedia · {artikel['artikel']}",
            "links": [{"titel": "Wikipedia-Artikel öffnen", "url": artikel["url"]}],
        }
        pruefung = artikel.get("pruefung")
        if mit_diagnose and pruefung and (
            not pruefung.get("wenn") or _symptom_passt(gesamt, pruefung["wenn"])
        ):
            quelle["pruefschritte"] = list(pruefung["schritte"])
            quelle["pruefhinweis"] = " ".join(pruefung["schritte"])
            quelle["links"].extend(pruefung["quellen"])
        ergebnis.append(quelle)
    return ergebnis


def suche(frage: str) -> list[dict]:
    """Findet ausdrücklich genannte Begriffe für die reine Begriffsauskunft."""
    return _finde("", frage, mit_diagnose=False)


def hintergrund(meldung: str, frage: str = "") -> list[dict]:
    """Findet bis zu zwei allgemeine Quellen zu Ticket und aktueller Rückfrage."""
    return _finde(meldung, frage, mit_diagnose=True)


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
    betriebsfrage = re.search(
        r"\b(?:was (?:soll|kann|muss) ich|(?:nächste\w*|erste\w*) (?:schritt\w*|prüfung\w*)|"
        r"was ist (?:jetzt |hier )?zu tun|wie (?:prüfe|behebe|löse) ich)\b", text)
    if kundendaten or betriebsfrage or not (ist_begriff or begriffsfrage):
        return ("Die lokalen Wikipedia-Artikel erklären IT-Begriffe. Für konkrete Werte oder "
                "Schritte in diesem Fall wähle die Ticketberatung oder die Kundendokumentation."), []
    return "\n\n".join(eintrag["text"] for eintrag in eintraege), eintraege
