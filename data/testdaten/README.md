# Testdaten

**Alles hier ist frei erfunden.** Keine echten Kunden, Personen, Tickets oder Zugangsdaten (DSGVO, Datenminimierung).

## Inhalt

| Datei | Inhalt |
|---|---|
| `tickets.json` | 30 Tickets (#1001 bis #1030) |
| `kunden.json` | 5 Testkunden |
| `doku/<kunde>.md` | Kundendoku je Testkunde, Zugangsdaten nur als Verweis auf den Passwortmanager |
| `erwartet.json` | Erwartete KI-Bewertung je Ticket (Priorität, Spam, Kategorie) für die Trefferquote |

## Aufbau der 30 Tickets

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

Die Zeitstempel sind fest (03.11. bis 19.11.2026). Bei der Präsentation sind sie Tage alt, dann zeigt die SLA-Ampel alles rot. Lösung folgt (Skript, das die Zeiten relativ zu "jetzt" verschiebt).

Die 30 ursprünglichen Tickets und ihre Sollwerte bilden die gemeinsame Referenz. Weitere Übungstickets #1031–1040 stehen separat in `uebungstickets.json`. Der Promptvergleich verwendet `tickets_promptvergleich.json`, die zusätzlichen Prioritätsprüfungen verwenden `prioritaet_blindtest.json` und `prioritaet_kontrolle.json`.
