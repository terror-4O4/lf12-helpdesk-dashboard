# Testdaten

**Alles hier ist frei erfunden.** Keine echten Kunden, Personen, Tickets oder Zugangsdaten (DSGVO, Datenminimierung).

## Inhalt

| Datei | Inhalt |
|---|---|
| `tickets.json` | 34 Tickets (#1001 bis #1034) mit Eingangsnachricht, Bearbeitungsstand und gegebenenfalls dokumentierter Lösung |
| `kunden.json` | 5 Testkunden |
| `doku/<kunde>.md` | Kundendoku je Testkunde, Zugangsdaten nur als Verweis auf den Passwortmanager |
| `erwartet.json` | Erwartete KI-Bewertung je Ticket (Priorität, Spam, Kategorie) für die Trefferquote |
| `fragen_doku.json` | Freie Doku-Fragen und Ticketfälle mit Sollfundstellen, fehlenden Treffern und einem Passwortmanager-Verweis |

Die Doku-Fälle lassen sich bei laufendem Backend mit `python scripts/auswertung_doku.py` prüfen. Die Auswertung trennt die Trefferquote für vorbereitete Fragen von Fällen ohne belegte Fundstelle und von der automatischen Suche zum Ticket.

## Aufbau der 34 Tickets

| | Anzahl |
|---|---|
| Geschlossen mit Lösungsweg (Grundlage für RAG) | 10 |
| Offen (neu, in Bearbeitung, warten, geparkt, Antwort erhalten) | 24 |
| Spam (Phishing, Werbung, Chef-Betrug, Schadsoftware-Anhang) | 4 |

| Priorität | Anzahl |
|---|---|
| `sehr_hoch` | 10 |
| `hoch` | 8 |
| `mittel` | 6 |
| `niedrig` | 10 |

**Schwierige Fälle**, die gezielt etwas prüfen (siehe Feld `hinweis` in `erwartet.json`):
- **Kein Spam trotz Spam-Wörtern:** #1012 (Kundin fragt, ob eine Mail echt ist), #1013 und #1025 (Konto gesperrt), #1021 (echte Warnung "Postfach fast voll", ähnlich wie Phishing #1003)
- **Spam ohne typische Merkmale:** #1010 (Werbung für Toner), #1011 (Chef-Betrug ohne Link)
- **Kundenregeln aus der Doku:** #1005, #1007, #1008, #1016, #1017, #1020 (Abschnitt "Besonderheiten")
- **Workaround vorhanden, daher nur mittel:** #1015, #1019, #1024

Die zusätzlichen Fälle bilden Rückfragen und Arbeitsausfälle aus dem Supportalltag ab. In #1031 meldet die Werkstatt, dass der Kartenleser am Nachbarplatz funktioniert. In #1032 fragt ein externer Wartungspartner nach dem vereinbarten Zutritt zum Technikraum. In #1033 bittet eine Praxis um Prüfung einer empfangenen Mail. In #1034 blockiert ein Buchungsfehler alle vier Versandplätze. Die festgelegten Fälle für den Promptvergleich und die RAG-Abnahme stehen in eigenen Dateien.

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
