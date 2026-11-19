# Datenformat

Gemeinsame Grundlage für Frontend, Backend und Testdaten. Wer ein Feld hinzufügen, umbenennen oder entfernen will, macht das **nur per Pull Request** und passt diese Datei mit an.

Alle Dateien liegen unter `data/testdaten/` und sind **frei erfunden**.

| Datei | Inhalt |
|---|---|
| `tickets.json` | Liste aller Tickets |
| `kunden.json` | Liste aller Kunden |
| `doku/<kunde>.md` | Kundendokumentation, eine Datei pro Kunde |
| `erwartet.json` | Erwartete KI-Bewertung je Ticket, nur für Tests |

## Allgemeine Regeln

- **Zeitstempel** im Format `JJJJ-MM-TTThh:mm:ss` in deutscher Ortszeit, z. B. `2026-11-19T08:12:00`
- **Feldnamen** klein, mit Unterstrich, ohne Umlaute (`erstellt_am`, nicht `erstelltAm`)
- **Kürzel** (z. B. Kunde) klein, ohne Leerzeichen und ohne Umlaute: `bau`, `steuerbuero`
- Ein noch nicht gesetzter Wert ist `null`

## Ticket

```json
{
  "id": 1042,
  "kunde": "bau",
  "titel": "Outlook startet nicht",
  "beschreibung": "Seit heute früh startet Outlook nicht mehr ...",
  "status": "neu",
  "prioritaet": "hoch",
  "prioritaet_quelle": "ki",
  "zugewiesen_an": null,
  "erstellt_am": "2026-11-19T08:12:00",
  "statushistorie": [
    { "status": "neu", "seit": "2026-11-19T08:12:00" }
  ],
  "ki": {
    "prioritaet": "hoch",
    "spam": false,
    "kategorie": "Software",
    "loesungsvorschlag": "...",
    "aehnliche_tickets": [1001]
  },
  "loesungsweg": null,
  "geschlossen_am": null
}
```

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | Zahl | Fortlaufende Ticketnummer. Im Dashboard angezeigt als **#1042**. Neues Ticket = höchste vorhandene ID + 1 |
| `kunde` | Text oder `null` | Kürzel aus `kunden.json`. `null`, wenn der Absender keinem Kunden zugeordnet werden kann (z. B. Spam) |
| `titel` | Text | Kurze Zusammenfassung |
| `beschreibung` | Text | Problembeschreibung, wie sie vom Kunden kommt |
| `status` | Text | Aktueller Status, siehe unten |
| `prioritaet` | Text oder `null` | Gültige Priorität, siehe unten. Wird zuerst von der KI gesetzt, kann von Hand geändert werden |
| `prioritaet_quelle` | Text oder `null` | `"ki"` = Wert stammt von der KI, `"manuell"` = von einem Mitarbeiter geändert |
| `zugewiesen_an` | Text oder `null` | Kürzel des zuständigen Mitarbeiters |
| `erstellt_am` | Zeitstempel | Wann das Ticket angelegt wurde |
| `statushistorie` | Liste | Jeder Statuswechsel mit Zeitpunkt, älteste zuerst. Daraus berechnet das Dashboard Ticketalter, Wartezeiten und SLA |
| `ki` | Objekt oder `null` | Ergebnis der KI-Auswertung, siehe unten. `null`, solange die KI das Ticket noch nicht bewertet hat |
| `loesungsweg` | Text oder `null` | Wird beim Schließen eingetragen. Daraus lernt die KI für ähnliche Fälle |
| `geschlossen_am` | Zeitstempel oder `null` | Wann das Ticket geschlossen wurde |

### Status

| Wert | Anzeige im Dashboard |
|---|---|
| `neu` | Neu (SLA läuft) |
| `in_bearbeitung` | In Bearbeitung |
| `warten_auf_kunde` | Warten auf Kunde |
| `antwort_erhalten` | Antwort erhalten |
| `geparkt` | Geparkt |
| `geschlossen` | Geschlossen |

### Priorität

`niedrig`, `mittel`, `hoch`, `sehr_hoch` (Stufen laut Projektantrag V2.1)

### KI-Block

Der KI-Block wird **nur von der KI** geschrieben, Mitarbeiter ändern ihn nie. Ändert ein Mitarbeiter die Priorität, passiert das im Feld `prioritaet` des Tickets (mit `prioritaet_quelle: "manuell"`), der KI-Block bleibt unverändert. So bleibt nachvollziehbar, was die KI vorgeschlagen hat. Das ist die Grundlage für die Tests („Wie oft lag die KI richtig?“).

Wird ein Ticket erneut analysiert, ersetzt das neue Ergebnis den KI-Block. Eine manuell gesetzte Priorität bleibt dabei erhalten.

| Feld | Typ | Bedeutung |
|---|---|---|
| `prioritaet` | Text | Von der KI vorgeschlagene Priorität |
| `spam` | true/false | Von der KI als Spam erkannt |
| `kategorie` | Text | Genau einer dieser Werte: `Software`, `Hardware`, `Netzwerk`, `Drucker`, `Benutzerkonto`, `E-Mail`, `Spam`, `Sonstiges` |
| `begruendung` | Text | Kurzer Satz, warum die KI so bewertet hat. Für das Dashboard und zum Nachvollziehen bei Tests |
| `loesungsvorschlag` | Text oder `null` | Vorschlag auf Basis ähnlicher gelöster Tickets und der Kundendoku |
| `aehnliche_tickets` | Liste von Zahlen | IDs der gelösten Tickets, auf die sich der Vorschlag stützt |

## Kunde

```json
{
  "kunde": "bau",
  "name": "Bauunternehmen GmbH",
  "branche": "Bau",
  "ort": "Wiesbaden",
  "ansprechpartner": "Herr Beispiel"
}
```

| Feld | Typ | Bedeutung |
|---|---|---|
| `kunde` | Text | Eindeutiges Kürzel, wird in Tickets und als Dateiname der Doku verwendet |
| `name` | Text | Anzeigename. **Immer Branche plus Rechtsform**, damit klar erfunden ist und nie einem echten Unternehmen entspricht |
| `branche` | Text | Branche des Kunden |
| `ort` | Text | Standort |
| `ansprechpartner` | Text | Erfundener Ansprechpartner (z. B. „Frau Muster“, „Herr Beispiel“) |

## Kundendoku

Eine Markdown-Datei pro Kunde unter `doku/<kunde>.md`, z. B. `doku/bau.md`. Feste Überschriften, damit die KI die passenden Abschnitte findet:

```
# <Name des Kunden>
## Umgebung
## Server
## Netzwerk und Firewall
## Drucker
## Software
## Zugangsdaten
## Besonderheiten
```

**Zugangsdaten stehen nie im Klartext in der Doku**, nur der Verweis auf den Passwortmanager:

```
- Firewall-Admin: siehe Passwortmanager, Eintrag "bau / Firewall"
```

## Erwartete Werte (Tests)

`erwartet.json` enthält für jedes Testticket die Bewertung, die ein Mitarbeiter vergeben würde. Damit lässt sich die Trefferquote der KI messen (Ziel laut Projektantrag: mindestens 80 %). Das Backend liest die Datei nicht, sie ist nur für Tests gedacht.

```json
{
  "id": 1012,
  "prioritaet": "niedrig",
  "spam": false,
  "kategorie": "E-Mail",
  "hinweis": "Kein Spam: echte Kundin fragt nach, enthält aber Phishing-Merkmale"
}
```

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | Zahl | Ticketnummer aus `tickets.json` |
| `prioritaet`, `spam`, `kategorie` | wie im KI-Block | Erwarteter Wert |
| `hinweis` | Text oder `null` | Warum so bewertet bzw. was das Ticket testet |

Abgrenzung der Kategorien in den Testdaten:

| Kategorie | Gehört dazu |
|---|---|
| `Software` | Programm startet nicht, stürzt ab, Fehlermeldung im Programm (auch Outlook als Programm) |
| `Hardware` | PC, Notebook, Monitor, Netzteil, Kartenlesegerät, sonstige Geräte außer Druckern |
| `Netzwerk` | Internet, WLAN, VPN, Verbindung zum Server |
| `Drucker` | Drucker, Multifunktionsgeräte inkl. Scannen, Etikettendrucker, Druckwarteschlange |
| `Benutzerkonto` | Konto gesperrt, Passwort, MFA, neue Benutzer, Rechte |
| `E-Mail` | Mailfluss, Postfach, Speicherplatz, Fragen zu verdächtigen Mails |
| `Spam` | Phishing, Werbung, Betrugsversuche ohne echtes IT-Anliegen |
| `Sonstiges` | Planung, Umzüge, Termine, kaufmännische Fragen |

Fragt ein echter Kunde, ob eine verdächtige Mail echt ist, ist das **kein Spam**, sondern ein IT-Anliegen (`E-Mail`).

## Testdaten und Arbeitskopie

Das Backend verändert **nie** die Dateien in `data/testdaten/`. Beim ersten Start kopiert es `tickets.json` nach `data/laufzeit/tickets.json` und arbeitet nur noch mit dieser Kopie (z. B. speichert es dort KI-Analysen). `data/laufzeit/` steht in der `.gitignore` und landet nie im Repo.

Zurücksetzen auf den Stand der Testdaten: `POST /api/testdaten/zuruecksetzen` oder den Ordner `data/laufzeit/` löschen.

## Offene Punkte

- **Testdaten altern:** Feste Zeitstempel sind bei der Präsentation Tage alt, dann ist jedes Ticket rot. Lösung folgt (z. B. Skript, das die Zeiten relativ zu „jetzt“ verschiebt).
- **Mitarbeiter:** Format für Mitarbeiter und persönliche To-dos folgt.
