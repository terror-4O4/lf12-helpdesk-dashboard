"""Ticketbelege und eindeutige Zuordnungen für die Support-Einschätzung."""

import re


# Der Betreff benennt das gemeldete Problem oft präziser als im Text erwähnte
# Begleitumstände (z. B. ein Programm, das auf einem zweiten Monitor stehen soll).
# Mehrdeutige Geräte- und Anwendungsbegriffe allein überschreiben kein Modellurteil.
FACHTHEMEN = {
    "Hardware": r"\b(?:monitore?\b|bildschirm\w*|netzteil\w*|kartenlese(?:r|gerät)\w*|tastatur\w*)",
    "Drucker": r"\b(?:\w*drucker\w*|druckwarteschlange\w*|kopierer\w*)",
    "Netzwerk": r"\b(?:vpn|wlan|internet|internetverbindung|internetausfall|netzwerkverbindung)\b",
    "Benutzerkonto": r"\b(?:benutzerkonto\w*|mfa|authenticator|konto gesperrt)\b",
    "E-Mail": r"\b(?:\w*postfach\w*|mailfluss|(?:e-)?mails?\b)",
    "Software": r"\b(?:\w*software|warenwirtschaft|outlook)\b",
    "Sonstiges": r"\b(?:terminbestätigung|wartungstermin|terminverschiebung)\b",
}
UMZUG = r"\b(?:umzug|büroumzug|standortwechsel)\b"
WUNSCH = r"\b(?:wunsch|beschaffung|anschaffung|bestellwunsch|kaufanfrage|angebotsanfrage)\b"
ANGEBOT = r"\b(?:bitte (?:um )?ein angebot|hätten? (?:gern|gerne)|angebot (?:anfordern|erbeten))\b"
STOERUNG = (r"\b(?:defekt\w*|ausfall|ausgefallen|kaputt|dringend|ersatzgerät|ersatzteil|"
            r"funktioniert nicht|arbeitet nicht|flackert|beschädigt|blockiert|kein bild|"
            r"schwarz|lässt sich nicht|geht nicht|startet nicht|fällt aus|fallen aus|"
            r"seit dem umzug|nach dem umzug|nicht (?:mehr )?arbeiten)\b")
POSTFACH_WARNUNG = (r"\b(?:fast voll|nahezu voll|beinahe voll|speicherwarnung)\b|"
                    r"\b(?:kontingent|speicherplatz|quota)\b.{0,30}\b(?:knapp|warnung)\b")
MAIL_AUSFALL = (r"\b(?:nicht mehr|keine?\b.{0,24}\bmehr|kein (?:versand|empfang)|"
                r"abgewiesen|unzustellbar|fehlgeschlagen|(?:versand|empfang) gestört)\b")
FLEXIBEL = r"\b(?:flexibel|kein zeitdruck|ohne zeitdruck|keine eile|kein fester termin)\b"
BETRIEBSSTOPP = (r"\b(?:warenausgang|versand|produktion|betrieb|abteilung) (?:steht(?=[.!?,;:]|$)|steht still|liegt still)\b|"
                 r"\b(?:niemand|keiner) kann (?:mehr |hier )?(?:arbeiten|buchen|abrechnen)\b|"
                 r"\b(?:wir|alle) können (?:alle |gar )?nicht (?:mehr )?arbeiten\b")
UMGEHUNG = (r"\b(?:weiterarbeiten|damit arbeiten|weich[te]\w* .{0,55} aus|"
            r"(?:am nachbarplatz|am ersatzplatz)\b.{0,50}\b(?:klappt|geht|funktioniert)|"
            r"(?:klappt|geht|funktioniert)\b.{0,45}\bam nachbarplatz|"
            r"(?:auf|über) usb(?:-stick)? (?:geht|funktioniert) (?:noch|weiterhin)|"
            r"(?:ersatzplatz|ersatzgerät|ausweichplatz) (?:funktioniert|steht zur verfügung))\b")
EINZELAUSFALL = r"\b(?:ich|er|sie) kann (?:gerade |gar |derzeit )*(?:nicht (?:mehr )?arbeiten|nicht weiterarbeiten)\b"
FUNKTIONS_AUSFALL = (r"\b(?:kein(?:e[ns]?)? (?:internet|netz|verbindung|zugriff|empfang)|"
                     r"(?:startet|verbinde[nt]\w*|anmelden|einschalten|starten|geht|funktioniert) (?:sich )?nicht|"
                     r"nicht (?:mehr )?(?:anmelden|einschalten|starten)|nicht (?:mehr )?erreichbar|"
                     r"konto gesperrt|stürzt (?:\w+ ){0,5}ab|schließt sich (?:sofort )?wieder|"
                     r"(?:anmeldung|zugriff) (?:nicht möglich|fehlgeschlagen)|"
                     r"(?:fehler|buchung)\b.{0,25}\b(?:fehlgeschlagen|bricht)\b|"
                     r"(?:fällt|fallen) aus|ausgefallen|ausfall)\b")
BREITER_AUSFALL = (r"\b(?:ganzen (?:büro|betrieb|standort)|gesamte[nr]? (?:büro|abteilung|filiale)|"
                   r"alle[nr]? (?:\w+ )?(?:arbeitsplätze[n]?|mitarbeitenden|versandplätzen|plätze)|"
                   r"kein(?:em|er) (?:der )?\w+ arbeitsplät\w*)\b")


def ticketstellen(ticket: dict) -> list[str]:
    """Betreff und wählbare Textstellen. Jeder Beleg stammt aus der Meldung."""
    stellen = [ticket["titel"].strip()]
    beschreibung = ticket["beschreibung"].strip()
    for satz in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ„\"0-9])|[\r\n]+", beschreibung):
        if satz and satz not in stellen:
            stellen.append(satz)
    return stellen


def eskalationsregeln(abschnitt: str, ticket: dict) -> list[str]:
    """Nur Prioritätsregeln mit konkretem fachlichem Bezug an das Modell geben."""
    text = " ".join([ticket["titel"], ticket["beschreibung"]]).casefold()
    unspezifisch = {"arbeitspl", "betriebe", "prioritä", "mehrere", "können", "werden",
                    "dadurch", "fällt", "fallen", "immer", "stehen", "daher", "programm"}
    regeln = []
    for zeile in abschnitt.splitlines():
        if "priorität" not in zeile.lower():
            continue
        woerter = {wort[:8] for wort in re.findall(r"[a-zäöüß]{6,}", zeile.casefold())}
        if any(wort in text for wort in woerter - unspezifisch):
            regeln.append(zeile.strip("- "))
    return regeln


def textstelle(stellen: list[str], muster: str) -> str | None:
    return next((s for s in stellen if re.search(muster, s.casefold())), None)


def thema(stellen: list[str]) -> str | None:
    """Mehrere plausible Fachgebiete bleiben der Modellbewertung überlassen."""
    titel = stellen[0].casefold()
    beschreibung = " ".join(stellen[1:]).casefold()
    # Ein physisches Einschaltproblem und eine Zugriffsfrage mit benanntem
    # Anmeldeverfahren grenzen den Gegenstand auch bei mehreren Produktnamen ein.
    if (re.search(r"\b(?:pc|notebook|rechner|laptop)\b", titel)
            and re.search(r"\b(?:einschalten|netzteil|ladeleuchte|kein bild|bleibt schwarz|geht nicht (?:mehr )?an)\b",
                          titel + " " + beschreibung)):
        return "Hardware"
    if (re.search(r"\b(?:anmeld\w*|benutzer\w*|mitarbeiter\w*)\b", titel)
            and re.search(FACHTHEMEN["Benutzerkonto"], beschreibung)):
        return "Benutzerkonto"
    texte = [titel, beschreibung]
    for text in texte:
        felder = [feld for feld, muster in FACHTHEMEN.items() if re.search(muster, text.casefold())]
        if felder:
            return felder[0] if len(felder) == 1 else None
    return None


def auswirkung(stellen: list[str], kundenregel: bool) -> tuple[str, str, str] | None:
    """Nur ausdrücklich beschriebene Arbeitsfolgen begründen eine Prioritätsregel."""
    stopp = textstelle(stellen, BETRIEBSSTOPP)
    if stopp:
        return "sehr_hoch", "Der gemeldete Ausfall stoppt einen Geschäftsbereich.", stopp
    # Freitext-Kundenregeln können mehrere Bedingungen enthalten. Der bloße
    # Treffer eines Gerätenamens belegt noch keine vertragliche Eskalation.
    if kundenregel:
        return None
    ausfall = next((s for s in stellen if re.search(FUNKTIONS_AUSFALL, s.casefold())
                    and not re.search(r"\b(?:kein(?:en)?|geplante[nr]?) ausfall\b|\b(?:falls|angenommen)\b",
                                      s.casefold())), None)
    umgehung = textstelle(stellen, UMGEHUNG)
    if umgehung and not re.search(r"\b(?:nicht|kein\w*)\b.{0,24}\b(?:weiterarbeiten|damit arbeiten|ersatzplatz|ersatzgerät)\b",
                                  umgehung.casefold()):
        return "mittel", "Die Meldung beschreibt, wie die Arbeit weitergehen kann.", umgehung
    umfang = textstelle(stellen, BREITER_AUSFALL)
    if umfang and ausfall:
        return "sehr_hoch", "Die Störung betrifft einen ganzen Bereich oder mehrere Arbeitsplätze.", umfang
    einzeln = textstelle(stellen, EINZELAUSFALL)
    if einzeln:
        return "hoch", "Eine Person meldet, dass sie nicht arbeiten kann.", einzeln
    if ausfall:
        return "hoch", "Eine benötigte Funktion wird als ausgefallen gemeldet.", ausfall
    return None


def supportbewertung(ticket: dict, modell: dict) -> dict:
    """Jedes Feld nennt seine Herkunft. Jede Begründung zitiert das Ticket."""
    stellen = ticketstellen(ticket)
    titel = stellen[0].casefold()
    gesamt = " ".join(stellen).casefold()
    wunsch = textstelle(stellen, WUNSCH + "|" + ANGEBOT)
    stoerung = re.search(STOERUNG, gesamt)
    umzug = re.search(UMZUG, titel) and not stoerung
    fach = "Sonstiges" if umzug else thema(stellen)
    regel = auswirkung(stellen, bool(modell.get("kundenregel")))
    mail_pruefen = (ticket.get("spampruefung") or {}).get("anliegen") == "mail_pruefen"
    if mail_pruefen:
        fach = "E-Mail"

    warnung = next((s for s in stellen if "postfach" in s.casefold()
                    and re.search(POSTFACH_WARNUNG, s.casefold())), None)
    if warnung and not mail_pruefen and not re.search(MAIL_AUSFALL, gesamt):
        fach = "E-Mail"
        regel = regel or ("mittel", "Das Ticket meldet eine Kapazitätswarnung am Postfach.", warnung)
    if not regel and umzug:
        flexibel = textstelle(stellen, FLEXIBEL)
        if flexibel:
            regel = "niedrig", "Der Umzug ist zeitlich flexibel planbar.", flexibel
    if not regel and wunsch and not stoerung:
        regel = "niedrig", "Die Anfrage beschreibt einen planbaren Beschaffungs- oder Änderungswunsch.", wunsch

    modellquelle = "mock" if modell.get("begruendung", "").startswith("[Mock]") else "modell"
    prioritaet = modell["prioritaet"]
    beleg = modell.get("beleg")
    if beleg not in stellen:
        beleg = stellen[0]
    if regel:
        prioritaet, grund, beleg = regel
    elif mail_pruefen:
        grund = "Der Absender bittet um Prüfung einer erhaltenen E-Mail."
        beleg = textstelle(stellen, r"\b(?:e-?mail|mail)\b") or stellen[0]
    elif fach:
        grund = f"Das Ticket nennt ein Thema aus dem Bereich {fach}."
        beleg = stellen[0] if umzug else (textstelle(stellen, FACHTHEMEN[fach]) or stellen[0])
    else:
        grund = "Einstufung anhand der markierten Ticketangabe."

    # Ein Auszug endet sichtbar mit Auslassung; die Ticketansicht enthält den vollen Text.
    zitat = beleg if len(beleg) <= 220 else beleg[:215].rsplit(" ", 1)[0] + " …"
    return {
        "prioritaet": prioritaet, "kategorie": fach or modell["kategorie"], "spam": False,
        "begruendung": f"{grund} Beleg: „{zitat}“",
        "bewertungsquellen": {"prioritaet": "regel" if regel else modellquelle,
                              "kategorie": "regel" if fach else modellquelle},
    }
