"""Ordnet eine neue Chatnachricht ein, bevor Ticketwissen in die Antwort einfließt."""

import json
import re

from fastapi import HTTPException

from backend import doku, ticketfragen


_TECHNIK = re.compile(
    r"\b(?:[\w-]*(?:server|software|drucker|datenbank|netzwerk|postfach|speicher|betriebssystem|"
    r"gerät|bildschirm|sensor|schnittstelle|terminal|client|konto|display|rechner|gateway|backup)\w*|"
    r"(?:wetter[- ]?)?apps?|anwendung\w*|hardware|vpn|wlan|lan|dns|dhcp|cpu|ram|usb|ip|api|"
    r"wifi|router|mail|outlook|windows|linux|passwort|browser|homepage|webseite|"
    r"treiber\w*|fehlermeldung\w*|netzteil|akku|laptop|monitor)\b", re.I)
_WETTER = re.compile(r"\b(?:wetter(?:bericht|vorhersage|prognose)?|regnet|schneit|regnen|schneien)\b", re.I)
_FREIZEIT = re.compile(
    r"\b(?:bundesliga|fußball(?:spiel|ergebnis)?|fussball(?:spiel|ergebnis)?|kochrezept|"
    r"lieblingsfarbe)\b|\b(?:erzähl\w*|mach\w*) (?:mir )?(?:einen |einen kurzen )?witz\b", re.I)
_KURZBEZUG = re.compile(
    r"(?:(?:und )?(?:warum|wie (?:bitte|genau)|was nun|was dann)|"
    r"was (?:prüfe|teste|mache|kontrolliere|vergleiche) ich(?: jetzt| zuerst| als nächstes)?|"
    r"(?:was|wie) (?:kann|soll|muss|können|sollen|müssen) (?:ich|wir) "
    r"(?:(?:jetzt|zuerst|genau|noch|dann|als nächstes|hier|etwas) )*(?:machen|tun|prüfen|vorgehen)|"
    r"(?:müssen|sollen) wir (?:etwas )?tun|(?:es |das )?(?:klappt|geht|funktioniert|leuchtet)"
    r"(?: jetzt| schon| wieder| immer noch| weiterhin| noch)?(?: nicht)?|(?:ja|nein|erledigt|ohne erfolg))"
    r"[.?! ]*", re.I)


def offensichtlich_fremd(frage: str) -> bool:
    # „Regnet es morgen?“ und „Bei Regen fällt unser WLAN aus“ brauchen verschiedene Antworten.
    return bool(_WETTER.search(frage) or _FREIZEIT.search(frage)) and not _TECHNIK.search(frage)


def _fallbegriffe(text: str) -> set[str]:
    text = re.sub(r"\breboot\w*", "Neustart", text, flags=re.I)
    return ticketfragen.fachbegriffe(text)


def themenbezug(frage: str, meldung: str = "", verlauf=(), modell=None) -> str:
    """Eindeutige Anliegen direkt durchlassen, sonst die aktuelle Nachricht lokal einordnen."""
    if offensichtlich_fremd(frage):
        return "fachfremd"
    technische_frage = bool(_TECHNIK.search(frage) or doku.ist_zugangsfrage(frage))
    if not meldung and technische_frage:
        return "it"
    if meldung:
        if (ticketfragen.kurze_rueckfrage(frage) or _KURZBEZUG.fullmatch(frage)
                or ticketfragen.fragt_nach_historie(frage)):
            return "ticket"
        if (_fallbegriffe(meldung) & _fallbegriffe(frage)
                or technische_frage and (doku.ist_zugangsfrage(frage) or ticketfragen.faktenfrage(frage)
                    or ticketfragen.fragt_nach_messwert(frage) or ticketfragen.ist_begriffsfrage(frage))):
            return "ticket"
        # Eine eigenständige Störung mit eigenem Objekt übernimmt keine Fakten aus dem offenen Ticket.
        if technische_frage and re.search(
                r"\bmein(?:e|en|er|em)?\s+|^wie (?:behebe|repariere|konfiguriere|installiere) ich\b",
                frage, re.I):
            return "it"
        # Befunde zu einem gerade ausgeführten Schritt können neue Fachwörter einführen.
        folgebefund = re.search(
            r"\b(?:bereits|inzwischen|immer noch|mittlerweile|jetzt (?:leer|voll|verbunden)|"
            r"(?:wieder|weiterhin) (?:an|aus|dunkel|hell)|beim (?:einstecken|einlesen))\b", frage, re.I)
        beobachtung = verlauf and re.match(
            r"(?:das|die|der|es) \w+(?: [\w-]+)? (?:leuchtet|blinkt|zeigt|bleibt|meldet|läuft)\b", frage, re.I)
        pruefergebnis = verlauf and re.match(
            r"(?:der|die|das) (?:selbsttest|test(?:seite|druck|ausdruck|lauf|ergebnis)|gegenprobe|"
            r"kontroll(?:anzeige|leuchte)) (?:ist|war) (?:\w+ ){0,3}"
            r"(?:leer|bedruckt|lesbar|erfolgreich|fehlgeschlagen|sichtbar|an|aus|grün|rot)\b", frage, re.I)
        if (folgebefund or beobachtung or pruefergebnis) and not (_WETTER.search(frage) or _FREIZEIT.search(frage)):
            return "ticket"

    if modell:
        nachricht = {"aktuelle_nachricht": frage, "ticket": meldung,
                     "letzte_nachrichten": list(verlauf[-2:])}
        try:
            text, _ = modell([
                {"role": "system", "content": (
                    "Ordne nur die aktuelle Nachricht in einem deutschen IT-Helpdesk ein. "
                    "ticket = Bitte um Hilfe zum offenen Fall, Rückfrage oder Beobachtung dazu. "
                    "it = eigenständige IT-Frage. fachfremd = erkennbar anderes Anliegen, "
                    "z.B. Wettervorhersage, Sportergebnis oder Freizeitplanung. "
                    "unklar = der Bezug lässt sich nicht erkennen. Die aktuelle Nachricht hat Vorrang. "
                    "Ein offenes Ticket macht einen Themenwechsel nicht zur Ticketfrage. "
                    "Eine Störung einer Wetter-App ist eine technische Frage. Antworte nur mit der Klasse.")},
                {"role": "user", "content": json.dumps(nachricht, ensure_ascii=False)},
            ], grammatik='root ::= "ticket" | "it" | "fachfremd" | "unklar"', temperatur=0, max_tokens=12)
            if text.strip() in {"ticket", "it", "fachfremd", "unklar"}:
                return text.strip()
        except HTTPException as fehler:
            if fehler.status_code not in (502, 504):
                raise
    return "it" if technische_frage else "unklar"


def hinweis(bezug: str, frage: str, *, im_ticket: bool) -> str:
    if bezug == "fachfremd":
        if _WETTER.search(frage):
            return "Aktuelle Wetterdaten kann ich hier nicht abrufen. Ich helfe dir bei IT-Fragen."
        return ("Hier helfe ich bei IT-Fragen. Was möchtest du zu diesem Ticket wissen?"
                if im_ticket else "Hier helfe ich bei IT-Fragen. Welche technische Frage hast du?")
    return ("Wie hängt deine Nachricht mit dem Ticket zusammen? Beschreibe kurz den betroffenen Vorgang."
            if im_ticket else "Bei welcher IT-Frage brauchst du Hilfe?")
