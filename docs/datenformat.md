# Datenformat

Gemeinsame Grundlage für Frontend, Backend und Testdaten. Wer ein Feld hinzufügen, umbenennen oder entfernen will, macht das **nur per Pull Request** und passt diese Datei mit an.

Alle Dateien liegen unter `data/testdaten/` und sind **frei erfunden**.

| Datei | Inhalt |
|---|---|
| `tickets.json` | Liste aller Tickets |
| `kunden.json` | Liste aller Kunden |
| `doku/<kunde>.md` | Kundendokumentation, eine Datei pro Kunde |
| `erwartet.json` | Erwartete KI-Bewertung je Ticket, nur für Tests |
| `fragen_doku.json` | Vorbereitete Doku-Fragen mit Sollfundstelle, Belegtext und Fällen ohne Treffer |
| `tickets_promptvergleich.json` | 20 neue Prüftickets mit Sollbewertung, fünf Fälle pro Priorität |
| `rag_abnahme.json` | Neue Prüffälle mit oder ohne bekannte Lösung in der Ticket-Historie |

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
  "ursache": null,
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
| `prioritaet_quelle` | Text oder `null` | `"ki"` bezeichnet eine automatisch übernommene Einstufung, `"manuell"` die Entscheidung eines Mitarbeiters. Die genaue Herkunft des Vorschlags steht unter `ki.bewertungsquellen`. |
| `zugewiesen_an` | Text oder `null` | Kürzel des zuständigen Mitarbeiters |
| `erstellt_am` | Zeitstempel | Wann das Ticket angelegt wurde |
| `statushistorie` | Liste | Jeder Statuswechsel mit Zeitpunkt, älteste zuerst. Daraus berechnet das Dashboard Ticketalter, Wartezeiten und SLA |
| `ki` | Objekt oder `null` | Ergebnis der KI-Auswertung, siehe unten. `null`, solange die KI das Ticket noch nicht bewertet hat |
| `spampruefung` | Objekt | Automatischer Eingangsbefund mit `verdaechtig` (boolescher Wert) und `begruendung` (Text). Bei einer erkannten Bitte um Prüfung einer E-Mail wird zusätzlich `anliegen: "mail_pruefen"` gesetzt. |
| `spam_entscheidung` | Text oder `null` | Entscheidung des Supports. `"spam"` bestätigt Spam, `"kein_spam"` gibt das Ticket frei. Der manuelle Entscheid hat Vorrang. |
| `ursache` | Text oder `null` | Ursache des Problems, wird beim Schließen eingetragen (laut Antrag „Ursache und Lösung erfassen“) |
| `loesungsweg` | Text oder `null` | Wird beim Schließen eingetragen, Pflicht zum Schließen (außer bestätigter Spam). Mit der Ursache die Grundlage für ähnliche Fälle |
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

| Code und Anzeige | Maßstab für die Sollbewertung |
|---|---|
| `niedrig` / Niedrig | Frage, kosmetischer Fehler oder planbarer Auftrag. Die laufende Arbeit ist möglich. |
| `mittel` / Normal | Die Arbeit ist beeinträchtigt. Ein nutzbarer Ausweichweg oder eine vorübergehende Unterbrechung erlaubt die Weiterarbeit. |
| `hoch` / Hoch | Eine Person kann eine notwendige Arbeit nicht erledigen oder eine wichtige Funktion ist ausgefallen. |
| `sehr_hoch` / Sehr dringend | Ein wesentlicher Geschäftsablauf steht oder mehrere Beschäftigte sind bei ihrer Arbeit blockiert. Ein wirksamer Ausweichweg fehlt. |

Bei der Sollbewertung zählen die im Ticket geschilderten Folgen. „Alle sehen die Meldung“ sagt noch nichts darüber aus, ob alle weiterarbeiten können. Ein bestelltes Ersatzgerät hilft erst, wenn es sich tatsächlich einsetzen lässt. Eine dokumentierte Kundenregel gilt, wenn das Ticket die darin genannten Bedingungen erfüllt.

### KI-Block

Der Block enthält die Ergebnisse der automatischen Supportbewertung und der Fallsuche. Eine manuelle Prioritätsänderung steht im Feld `prioritaet` des Tickets und hat Vorrang vor späteren Vorschlägen.

Eine erneute Ticketanalyse aktualisiert Priorität, Kategorie und Begründung. Ergebnisse der Fallsuche und die manuell gesetzte Priorität bleiben erhalten. Die Spam-Warteschlange verwendet den Eingangsbefund und die Entscheidung des Supports.

| Feld | Typ | Bedeutung |
|---|---|---|
| `prioritaet` | Text | Automatisch vorgeschlagene Priorität |
| `bewertungsquellen` | Objekt oder `null` | Herkunft je Feld (`prioritaet`, `kategorie`). Mögliche Werte sind `modell`, `regel` und `mock`. Bei alten Einträgen kann die Herkunft fehlen. |
| `spam` | boolescher Wert oder `null` | Kompatibilitätsfeld älterer Bewertungen. Für die Spam-Prüfung gilt `spampruefung` auf Ticketebene. |
| `kategorie` | Text | Fachgebiet des Supportfalls. Ältere Modellvergleiche verwenden zusätzlich die Klasse `Spam`. |
| `begruendung` | Text | Erläuterung der Einstufung mit einem Beleg aus Betreff oder Beschreibung |
| `loesungsvorschlag` | Text oder `null` | Vorschlag auf Basis ähnlicher gelöster Tickets als Text, oder „Kein passender gelöster Fall gefunden …“. `null` = noch nicht gesucht |
| `ursachen` | Liste | Bis zu 3 Vorschläge `{"ursache", "loesungsweg", "tickets": [1001]}`, wahrscheinlichste zuerst. Leer, wenn kein Fall passt |
| `aehnliche_tickets` | Liste von Zahlen | IDs der gelösten Tickets, auf die sich die Vorschläge stützen |
| `treffer` | Liste | Ergebnis der Suche vor der KI: `{"id", "aehnlichkeit"}` (0 bis 1), bester zuerst. Zeigt auch Fälle, die die KI verworfen hat |

Eingangsprüfung, Bewertung und Fallsuche sind eigenständige Schritte. Wurde nur nach gelösten Fällen gesucht, kann das Ticket bereits Fallvorschläge enthalten, während Priorität, Kategorie und Begründung im KI-Block noch fehlen.

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

Weitere Überschriften auf Ebene `##` bilden zusätzliche Fundstellen. Die Suche gibt aus Dateiname und Überschrift eine Quellenkennung wie `doku/bau.md#netzwerk-und-firewall` an. Portal-Links als Markdown-Links pflegen. Die Antwort übernimmt die Adresse aus der Kundenakte.

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
| `aehnlich` | Liste von Zahlen oder `null` | Welches gelöste Ticket passt. `[1001]` = muss unter den Top 3 erscheinen, `[]` = kein passender Fall (die KI darf nichts erfinden), `null` = nicht Teil des RAG-Tests (gelöste Tickets und Spam) |
| `aehnlich_hinweis` | Text oder `null` | Warum dieser Fall passt bzw. warum keiner passt |

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

Diese Abgrenzung steht auch im Analyse-Prompt der KI (`KATEGORIE_BESCHREIBUNG` in `backend/app.py`). Wer sie ändert, passt beide Stellen an.

## Wissensbasis (ähnliche Tickets)

In die Wissensbasis kommt jedes Ticket mit Status `geschlossen` und Lösungsweg, das kein Spam ist. Verglichen wird nur das Problem (Titel und Beschreibung), nicht die Lösung. Die Vektoren liegen in `data/laufzeit/wissensbasis.json` (nicht im Repo) und werden beim Suchen automatisch ergänzt, wenn ein Ticket neu geschlossen oder geändert wurde.

## Testdaten und Arbeitskopie

Beim ersten Laden erstellt das Backend aus `data/testdaten/tickets.json` und `data/testdaten/uebungstickets.json` die Arbeitskopie `data/laufzeit/tickets.json`. Dort speichert es auch neue Meldungen und KI-Analysen. Git ignoriert das Verzeichnis `data/laufzeit/`.

`POST /api/testdaten/ergaenzen` ergänzt fehlende Übungsfälle in der Arbeitskopie. Das Feld `uebungsvorlage` merkt sich die Nummer der Vorlage, falls die lokale Ticketnummer bereits vergeben ist. So bleiben wiederholte Importe und spätere Bearbeitungen demselben Fall zugeordnet.

Der Endpunkt `POST /api/testdaten/zuruecksetzen` ersetzt die Ticket-Arbeitskopie durch den Testdatenstand. Für eine reproduzierbare Demo lässt sich die Uhrzeit mit `?jetzt=2026-11-19T11:30` an die Testdaten anpassen.

## Offene Punkte

- **Mitarbeiter:** Das Dashboard nimmt die Kürzel aus `zugewiesen_an`. Persönliche To-dos werden im Browser gespeichert.
