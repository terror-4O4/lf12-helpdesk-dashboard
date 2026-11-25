# Testdaten

**Alles hier ist frei erfunden.** Keine echten Kunden, Personen, Tickets oder Zugangsdaten (DSGVO, Datenminimierung).

## Inhalt

| Datei | Inhalt |
|---|---|
| `tickets.json` | Die 30 ursprünglichen Projekttickets (#1001–1030) für die Modellmessung |
| `uebungstickets.json` | Zehn zusätzliche Übungsfälle (#1031–1040) für die Arbeit im Dashboard |
| `kunden.json` | 5 Testkunden |
| `doku/<kunde>.md` | Kundendoku je Testkunde, Zugangsdaten nur als Verweis auf den Passwortmanager |
| `erwartet.json` | Die ursprünglichen Sollwerte für genau diese 30 Tickets (Priorität, Spam, Kategorie) |
| `fragen_doku.json` | Freie Doku-Fragen und Ticketfälle mit Sollfundstellen, fehlenden Treffern und einem Passwortmanager-Verweis |
| `prioritaet_blindtest.json` | 20 separat erstellte Supporttickets für den lokalen Vergleich der Dashboard-Priorisierung, fünf je Soll-Stufe |
| `prioritaet_kontrolle.json` | Zwölf weitere Supporttickets zur Kontrolle der gewählten Modellvariante, drei je Stufe |

Die Doku-Fälle lassen sich bei laufendem Backend mit `python scripts/auswertung_doku.py` prüfen. Die Auswertung trennt die Trefferquote für vorbereitete Fragen von Fällen ohne belegte Fundstelle und von der automatischen Suche zum Ticket.

## Aufbau der 30 ursprünglichen Tickets

| | Anzahl |
|---|---|
| Geschlossen mit Lösungsweg (Grundlage für RAG) | 10 |
| Offen (neu, in Bearbeitung, warten, geparkt) | 20 |
| Spam (Phishing, Werbung, Chef-Betrug, Schadsoftware-Anhang) | 4 |

| Priorität | Anzahl |
|---|---|
| `sehr_hoch` | 9 |
| `hoch` | 8 |
| `mittel` | 5 |
| `niedrig` | 8 |

**Schwierige Fälle**, die gezielt etwas prüfen (siehe Feld `hinweis` in `erwartet.json`):
- **Kein Spam trotz Spam-Wörtern:** #1012 (Kundin fragt, ob eine Mail echt ist), #1013 und #1025 (Konto gesperrt), #1021 (echte Warnung "Postfach fast voll", ähnlich wie Phishing #1003)
- **Spam ohne typische Merkmale:** #1010 (Werbung für Toner), #1011 (Chef-Betrug ohne Link)
- **Kundenregeln aus der Doku:** #1005, #1007, #1008, #1016, #1017, #1020 (Abschnitt "Besonderheiten")
- **Workaround vorhanden, daher nur mittel:** #1015, #1019, #1024

### Übungstickets im Dashboard

Die ursprünglichen 30 Tickets und ihre Sollwerte kommen aus dem gemeinsamen Projekt auf `main`. Die zehn zusätzlichen Fälle wurden für die lokale Variante erstellt. Eine neue Arbeitskopie enthält alle 40 Tickets. Die Hauptmessung verwendet ausschließlich #1001–1030.

| Übung | Fachlich erwartete Einstufung | Entscheidende Angabe |
|---|---|---|
| #1031 | Hardware, mittel, regulär | Derselbe Kartenleser funktioniert am Nachbarplatz. |
| #1032 | Sonstiges, niedrig, regulär | Ein externer Wartungspartner fragt nach einem vereinbarten Termin. |
| #1033 | E-Mail, niedrig, regulär | Die Praxis meldet eine verdächtige Mail zur Prüfung. Der Mailbetrieb läuft. |
| #1034 | Software, sehr hoch, regulär | Alle vier Versandplätze sind blockiert, auch mit einem anderen Konto. |

#1035 und #1036 vergleichen einen Scanfehler mit nutzbarer manueller Eingabe und einen Versandstillstand trotz manueller Eingabe. #1037–1040 behandeln ein stummes Teams-Mikrofon, einen veralteten Bauplan, eine geplante Kalenderfreigabe und unerbetene Bannerwerbung.

In einer bereits bearbeiteten Arbeitskopie ergänzt `POST /api/testdaten/ergaenzen` die fehlenden Übungsfälle. Belegte Ticketnummern bleiben beim bisherigen Vorgang, die neue Vorlage erhält dann eine freie Nummer. Die Antwort enthält die neu vergebenen Ticketnummern.

**Paare für den Lösungsvorschlag (RAG):** Zu diesen offenen Tickets gibt es ein ähnliches gelöstes Ticket, meist vom selben Kunden.

| Offen | Gelöst |
|---|---|
| #1022 Outlook schließt sich | #1001 Outlook startet nicht |
| #1002 Lagerdrucker | #1005 Druckwarteschlange |
| #1017 Kanzleisoftware startet nicht | #1016 Datenbank nicht erreichbar |
| #1021 Postfach fast voll | #1020 Keine externen Mails |
| #1026 VPN Bauleiter-Notebook | #1004 VPN nach Update |
| #1025 Konto gesperrt (anderer Kunde) | #1013 Konto gesperrt |

## Hinweis Zeitstempel

Die Beispiele verwenden feste Zeitstempel. Die [Demo-Uhrzeit im Dashboard](http://127.0.0.1:8000/?jetzt=2026-11-19T11:30) zeigt den Stand am 19. November um 11:30 Uhr.
