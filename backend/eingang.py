"""Lokale Eingangsprüfung auf unerwünschte Nachrichten für den IT-Support."""

import re


def pruefe(ticket: dict) -> dict:
    """Vormerken nur bei einem konkreten Muster aus Inhalt, Absicht und Aufforderung."""
    titel = (ticket.get("titel") or "").casefold()
    nachricht = (ticket.get("beschreibung") or "").casefold()
    text = " ".join((titel + " " + nachricht).split())

    # Bei ausdrücklich zitierten Fremdangeboten zählt die Bitte des Kunden.
    ohne_zitat = re.sub(r'"[^"]+"|„[^“”]+[“”]|»[^«]+«|«[^»]+»', ' ', text)
    if (ohne_zitat != text
            and re.search(r"\b(?:lieferantenangebot|lieferant(?:en)?|fremdangebot)\b", ohne_zitat)
            and re.search(r"\b(?:wir (?:benötigen|brauchen)|für uns|bestellung.{0,35}(?:auslösen|freigeben))\b", ohne_zitat)):
        text = ohne_zitat

    # Eine Bitte um Prüfung kann den verdächtigen Originaltext wörtlich enthalten.
    meldet_nachricht = (
        re.search(r"(?:ist|war) (?:diese?|die) (?:(?:e-?)?mail|nachricht) (?:echt|gefährlich|seriös)", text)
        or re.search(r"verdächtige[nr]? (?:(?:e-?)?mail|nachricht).{0,45}(?:erhalten|bekommen|prüfen|prüft|gemeldet)", text)
        or re.search(r"(?:bitte|könn(?:t|en) (?:ihr|sie)).{0,24}(?:prüfen|prüft|einschätzen|kontrollieren).{0,45}(?:diese |beigefügte |verdächtige )(?:mail|nachricht)", text)
        or re.search(r"(?:habe|haben|hat).{0,65}(?:mail|nachricht).{0,24}(?:erhalten|bekommen).{0,120}(?:echt|phishing|verdächtig|prüfen|was (?:soll|tun))", text)
        or re.search(r"(?:könn(?:t|en) (?:ihr|sie)|bitte).{0,35}(?:mail|nachricht|anhang).{0,20}prüfen", text)
        or re.search(r"(?:ist|war|könnte).{0,12}(?:das|dies).{0,18}phishing", text)
        or re.search(r"(?:phishing|spam|verdächtige (?:(?:e-?)?mail|nachricht)).{0,20}(?:melden|meldung|zur prüfung)", titel)
    )
    if meldet_nachricht:
        befund = {"verdaechtig": False, "begruendung": "Der Absender bittet den Support um Prüfung einer Nachricht."}
        if re.search(r"\b(?:e-?mail|mail)\b", text):
            befund["anliegen"] = "mail_pruefen"
        return befund

    grund = None
    if (re.search(r"(?:passwort|kennwort|zugangsdaten|anmeldedaten|kontodaten|ihre daten)", text)
            and re.search(r"(?:bestätigen|verifizieren|aktualisieren|geben|tragen) sie\b|\b(?:gib|bestätige|verifiziere|aktualisiere)\b|jetzt.{0,30}(?:bestätigen|verifizieren|eingeben)", text)
            and re.search(r"(?:link|formular|anmeldeseite)", text)):
        grund = "Die Nachricht fordert zur Eingabe oder Bestätigung von Zugangsdaten über einen Link oder ein Formular auf."
    elif (re.search(r"(?:gutschein(?:karte)?n?|geschenkkarten?)", text)
          and re.search(r"(?:codes?|nummern?|pins?)", text)
          and re.search(r"(?:schick(?:en sie|e? mir)|send(?:en sie|e mir)|übermitteln sie|weiterleiten an)", text)):
        grund = "Die Nachricht verlangt Gutscheine und die Übermittlung ihrer einlösbaren Codes."
    elif (re.search(r"(?:rechnung|zahlung|betrag begleichen)", text)
          and re.search(r"(?:zip[- ]?(?:anhang|archiv|datei)|\.zip\b)", text)
          and re.search(r"(?:mahngebühr|letzte mahnung|inkasso|innerhalb von \d+ stunden)", text)):
        grund = "Eine Zahlungsaufforderung verbindet ein ZIP-Archiv mit einer kurzen Frist oder angedrohten Mahnfolgen."
    elif (re.search(r"(?:\d+\s*%|rabatt|halben preis|sonderpreis|gratis|sparangebot|sonderangebot)", text)
          and re.search(r"(?:jetzt|heute|sofort).{0,35}(?:bestellen|kaufen|zugreifen|sichern|buchen)", text)):
        grund = "Die Nachricht bewirbt eine Vergünstigung und fordert direkt zum Kauf oder zur Buchung auf."
    elif (re.search(r"\bunser(?:em|en|er)?\b.{0,26}\b(?:katalog|newsletter|sortiment|kollektion)\b", text)
          and re.search(r"\b(?:bestellen|kaufen|buchen) sie\b|\bjetzt.{0,20}(?:bestellen|kaufen|buchen)\b", text)):
        grund = "Der Absender bewirbt sein eigenes Sortiment und fordert den Empfänger zum Kauf auf."

    return {"verdaechtig": grund is not None,
            "begruendung": grund or "Die lokale Eingangsprüfung hat keinen Spamhinweis gefunden."}


def ist_spam(ticket: dict) -> bool:
    """Die Entscheidung des Supports gilt vor dem automatischen Prüfbefund."""
    entscheidung = ticket.get("spam_entscheidung")
    if entscheidung is not None:
        return entscheidung == "spam"
    return (ticket.get("spampruefung") or pruefe(ticket))["verdaechtig"]
