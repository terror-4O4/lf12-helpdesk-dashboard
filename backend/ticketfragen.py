"""Aus Ticketmeldungen, dokumentierten Arbeitsschritten und Quellen lesbare Antworten bilden."""

import re

from backend import doku, rag


def handlungsfrage(frage: str) -> bool:
    return bool(re.search(
        r"\b(?:tun|vorgehen|vorgang|vorschlag|empfehlen|empfiehlst|schritte?|handeln|"
        r"handlungsbedarf|nächste[snr]?|weiter|beheben|lösen|reagieren|"
        r"wie (?:gehe|gehen|mache|mach|erledige|prüfe|prüfen)|was (?:kann|soll|muss))\b",
        frage, re.I))


def fragt_nach_messwert(frage: str) -> bool:
    return bool(re.search(r"\b(?:wie (?:viel|voll|groß|hoch)|wie(?:viel|\s+viele) (?:gb|mb|prozent)|"
                          r"aktuell\w* (?:belegung|füllstand|messwert)|(?:frei|belegt)\s*\?)", frage, re.I))


def fragt_nach_historie(frage: str) -> bool:
    return bool(re.search(r"\b(?:damals|vergleichsfall|(?:ähnlich|früher|gelöst)\w* (?:gelöst\w* )?(?:fall|fälle|ticket)\w*)\b",
                          frage, re.I))


def anschlussfrage(frage: str) -> bool:
    return bool(re.fullmatch(r"(?:und )?(?:(?:wie|wo) (?:genau|mache ich das|geht das|finde ich das|sehe ich das)"
                             r"|was (?:dann|genau)|und dann|warum|wieso|wo genau|kannst du das erklären)[?!. ]*",
                             frage.strip(), re.I))


def anleitung(abschnitte: list[doku.Abschnitt], meldung: str) -> doku.Abschnitt | None:
    """Eine Anleitung muss ihr Thema im aktuellen Ticket wiederfinden."""
    for abschnitt in abschnitte:
        if not abschnitt.titel.startswith("Vorgehen bei "):
            continue
        thema = abschnitt.titel.removeprefix("Vorgehen bei ").casefold()
        woerter = set(re.findall(r"[a-zäöüß]{4,}", thema))
        if woerter and all(wort in meldung.casefold() for wort in woerter):
            return abschnitt
    return None


def passt_zur_frage(abschnitt: doku.Abschnitt, frage: str) -> bool:
    """Offene Rückfragen beziehen sich aufs Ticket. Ein neues Thema braucht einen eigenen Beleg."""
    hinweiswoerter = {"bitte", "etwas", "mache", "müssen", "weiter", "schritt", "schritte", "genau",
                     "muss", "kann", "soll", "sollen", "können", "jetzt", "nächste", "nächsten", "diesem",
                     "diese", "prüfe", "prüfen", "tun", "frage", "ticket", "gibt", "bekomme", "heute", "einen",
                     "eine", "wäre", "welcher", "welche", "hoch", "viel", "dann", "damit", "hier", "handeln",
                     "reagieren", "empfiehlst", "empfehlen", "vorgehen", "unser", "sinnvoll"}
    fachwoerter = {w for w in re.findall(r"[a-zäöüß]{3,}", frage.casefold())
                   if w not in hinweiswoerter and w not in {"was", "wie", "der", "das", "den", "die", "wir",
                                                            "ich", "sie", "ihr", "mir", "mit", "als", "ist", "bei"}}
    quelle = (abschnitt.titel + " " + arbeitsschritte(abschnitt)).casefold()
    return not fachwoerter or any(w in quelle for w in fachwoerter)


def fallquelle(ticket: dict) -> dict:
    return {"titel": ticket["titel"], "quelle": f"Ticket #{ticket['id']}", "ticket_id": ticket["id"],
            "text": ticket.get("loesungsweg") or "", "links": []}


def arbeitsschritte(abschnitt: doku.Abschnitt) -> str:
    return "\n\n".join(p.strip() for p in abschnitt.text.split("\n\n")
                       if p.strip() and not p.startswith(("Vergleichsfall:", "[")))


def aus_anleitung(abschnitt: doku.Abschnitt, ticket: dict, bestand: list[dict], frage: str) -> tuple[str, list]:
    antwort = arbeitsschritte(abschnitt)
    if fragt_nach_messwert(frage):
        antwort = "Der Assistent hat keinen Zugriff auf aktuelle Messwerte dieses Systems. " + antwort
    else:
        antwort += "\n\nAktuelle Messwerte stehen dem Assistenten nicht zur Verfügung."
    quellen = [abschnitt.als_quelle()]
    verweise = {int(nr) for nr in re.findall(r"^Vergleichsfall:\s*#(\d+)\s*$", abschnitt.text, re.M)}
    for fall in bestand:
        if (fall["id"] in verweise and fall["id"] != ticket["id"] and ticket.get("kunde")
                and fall.get("kunde") == ticket["kunde"] and rag.ist_fall(fall)):
            info = fall.get("ursache") or fall["titel"]
            hinweis = f"Im früheren Ticket #{fall['id']} wurde Folgendes festgestellt: {info.rstrip('.')}."
            if fragt_nach_historie(frage):
                return hinweis + "\n\nDokumentierter Lösungsweg: " + fall["loesungsweg"], [fallquelle(fall)]
            antwort += "\n\n" + hinweis
            quellen.append(fallquelle(fall))
    if fragt_nach_historie(frage) and len(quellen) == 1:
        return "Zu diesem Vorgehen ist kein bestätigter Vergleichsfall des Ticketkunden hinterlegt.", []
    return antwort, quellen


def ist_begriffsfrage(frage: str) -> bool:
    if re.search(r"\b(?:unser\w*|mein\w*|hier|aktuell\w*|für uns|unsere[rn]?)\b", frage, re.I):
        return False
    return bool(re.search(r"\b(?:was (?:ist ein\w*|bedeutet|heißt|sind)|erklär\w*|wofür steht|was versteht man unter)\b",
                          frage, re.I))
