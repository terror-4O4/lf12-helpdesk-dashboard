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
BETRIEBSSTOPP = (r"\b(?:warenausgang|versand|produktion|betrieb|abteilung|betriebsteil) (?:steht(?=[.!?,;:]|$)|steht still|liegt still)\b|"
                 r"\b(?:betriebsstillstand|produktionsstillstand|betriebsausfall)\b")
GRUPPE_BLOCKIERT = (r"\b(?:niemand kann|keiner kann|kann niemand|kann keiner)\b.{0,55}\b(?:arbeiten|buchen|abrechnen|anmelden|aufträge bearbeiten)\b|"
                    r"\b(?:wir|alle) können (?:alle |gar )?nicht (?:mehr )?arbeiten\b|"
                    r"\b(?:die (?:schicht|abteilung|filiale)|das team) kann\b.{0,40}\bkeine?\w*\b.{0,55}"
                    r"\b(?:annehmen|ausliefern|bearbeiten|abschließen|freigeben|versenden|abrechnen|verbuchen)\b")
UMGEHUNG = (r"\b(?:weiterarbeiten|damit arbeiten|weich[te]\w* .{0,55} aus|"
            r"(?:am nachbarplatz|am ersatzplatz)\b.{0,50}\b(?:klappt|geht|funktioniert)|"
            r"(?:klappt|geht|funktioniert)\b.{0,45}\bam nachbarplatz|"
            r"(?:auf|über) usb(?:-stick)? (?:geht|funktioniert) (?:noch|weiterhin)|"
            r"(?:ersatzplatz|ersatzgerät|ausweichplatz) (?:funktioniert|steht zur verfügung)|"
            r"(?:läuft|geht) (?:damit|dort) weiter|"
            r"(?:kann|können|lassen sich|lässt sich)\b.{0,90}\b(?:weiter \w+en|von hand|per hand|manuell)|"
            r"(?:ersatzweise|behelfsweise|stattdessen)\s+(?:nutzen|verwenden|arbeiten|kann|können)|"
            r"(?:arbeiten|kommen)\b.{0,35}\blangsamer (?:weiter|voran))\b")
EINZELAUSFALL = r"\b(?:ich|er|sie) kann (?:gerade |gar |derzeit )*(?:nicht (?:mehr )?arbeiten|nicht weiterarbeiten)\b"
FUNKTIONS_AUSFALL = (r"\b(?:kein(?:e[ns]?)? (?:internet|wlan|netz|verbindung|zugriff|empfang)|"
                     r"(?:startet|verbinde[nt]\w*|anmelden|einschalten|starten|geht|funktioniert) (?:sich )?nicht|"
                     r"nicht (?:mehr )?(?:anmelden|einschalten|starten)|nicht (?:mehr )?erreichbar|"
                     r"konto gesperrt|stürzt (?:\w+ ){0,5}ab|schließt sich (?:sofort )?wieder|"
                     r"(?:anmeldung|zugriff) (?:nicht möglich|fehlgeschlagen)|"
                     r"(?:fehler|buchung)\b.{0,25}\b(?:fehlgeschlagen|bricht)\b|"
                     r"(?:wird|werden|wurde|wurden)\b.{0,50}\b(?:abgewiesen|zurückgewiesen|abgelehnt|blockiert)|"
                     r"(?:frier\w*)\b.{0,60}\bein|(?:fällt|fallen) aus|ausgefallen|ausfall)\b")
BREITER_AUSFALL = (r"\b(?:ganzen (?:büro|betrieb|standort)|gesamte[nr]? (?:büro|abteilung|filiale)|"
                   r"(?:alle[nr]?|sämtliche[nr]?|mehrere[nr]?) (?!anderen?\b|übrigen?\b)(?:\w+ )?"
                   r"(?:arbeitsplätz\w*|mitarbeiter\w*|mitarbeitenden|beschäftigten|personen|nutzer\w*|"
                   r"sachbearbeiter\w*|\w*stationen|\w*plätzen?|plätze)|"
                   r"kein(?:em|er) (?:der )?\w+ arbeitsplät\w*)\b")

# Eine erwartete oder inzwischen behobene Störung beschreibt keine gegenwärtige Auswirkung.
HYPOTHETISCH = r"\b(?:falls|angenommen|möglicherweise|vielleicht|könnte[n]?|würde[n]?|im falle|für den fall)\b"
VERNEINT = r"\b(?:kein(?:en|e)?|geplante[nr]?|befürchtete[nr]?) (?:betriebs)?(?:ausfall|stillstand)\b"
WIEDER_HERGESTELLT = (r"\b(?:inzwischen|mittlerweile|jetzt|wieder)\b.{0,50}\b(?:alles|betrieb|versand|arbeit|system)\b"
                       r".{0,45}\b(?:wieder normal|störungsfrei|einwandfrei|in ordnung)\b|"
                       r"\b(?:störung|ausfall|problem) (?:ist|wurde) (?:inzwischen |bereits )?(?:behoben|beseitigt)\b")
KEIN_ERSATZ = (r"\b(?:nicht|kein\w*|unmöglich|fehlt|fehlen|gesperrt|scheitert|ohne zugang)\b|"
               r"\b(?:damit|um)\b.{0,45}\bwieder weiterarbeiten\b|"
               r"\b(?:die |alle )?(?:anderen|übrigen)\b.{0,40}\b(?:arbeiten|weiterarbeiten|läuft|geht)\b")


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


def auswirkung(stellen: list[str], kundenregel: bool, modellprioritaet: str) -> tuple[str, str, str] | None:
    """Nur ausdrücklich beschriebene Arbeitsfolgen begründen eine Prioritätsregel."""
    aktuell = []
    for stelle in stellen:
        if re.search(WIEDER_HERGESTELLT, stelle.casefold()):
            aktuell.clear()
        elif not stelle.endswith("?") and not re.search(HYPOTHETISCH + "|" + VERNEINT, stelle.casefold()):
            aktuell.append(stelle)
    stopp = textstelle(aktuell, BETRIEBSSTOPP)
    if stopp:
        return "sehr_hoch", "Der gemeldete Ausfall stoppt einen Geschäftsbereich.", stopp
    ausfall = textstelle(aktuell, FUNKTIONS_AUSFALL)
    # Den erfolgreichen Ersatzweg im eigenen Teilsatz prüfen. Ein funktionierender
    # anderer Geschäftsbereich oder ein erst erbetenes Ersatzgerät ist kein Ersatzweg.
    stoerung = ausfall or textstelle(aktuell, STOERUNG + r"|\b(?:störung|eingeschränkt|langsamer|fehlt|nicht (?:mehr )?erkannt)\b")
    umgehung = next((teil for s in aktuell for teil in re.split(r",\s*|\s+aber\s+", s)
                     if re.search(UMGEHUNG, teil.casefold()) and not re.search(KEIN_ERSATZ, teil.casefold())), None)
    if stoerung and umgehung and not (kundenregel and modellprioritaet in ("hoch", "sehr_hoch")):
        return "mittel", "Die Meldung beschreibt, wie die Arbeit weitergehen kann.", umgehung
    gruppenausfall = textstelle(aktuell, GRUPPE_BLOCKIERT)
    if not gruppenausfall and ausfall:
        for stelle in aktuell:
            satz = stelle.casefold()
            if (re.search(BREITER_AUSFALL, satz)
                    and re.search(FUNKTIONS_AUSFALL + r"|\b(?:betroffen|betrifft)\b", satz)
                    and not re.search(r"\b(?:nicht|niemand) betroffen\b", satz)):
                gruppenausfall = stelle
                break
    if gruppenausfall:
        return "sehr_hoch", "Die Meldung beschreibt einen gemeinsamen Arbeitsausfall.", gruppenausfall
    # Bei einer möglichen kundenspezifischen Eskalation die höhere Modellstufe
    # erhalten. Ein bloßes gemeinsames Schlagwort darf eine klare Störung nicht herabstufen.
    if kundenregel and modellprioritaet in ("hoch", "sehr_hoch"):
        return None
    einzeln = textstelle(aktuell, EINZELAUSFALL)
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
    wunsch = textstelle(stellen[:1], WUNSCH) or textstelle(stellen, ANGEBOT)
    stoerung = re.search(STOERUNG, gesamt)
    umzug = re.search(UMZUG, titel) and not stoerung
    fach = "Sonstiges" if umzug else thema(stellen)
    regel = auswirkung(stellen, bool(modell.get("kundenregel")), modell["prioritaet"])
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
    elif modell.get("beleg") in stellen:
        grund = "Das Sprachmodell stützt die Priorität auf die folgende Ticketangabe."
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
