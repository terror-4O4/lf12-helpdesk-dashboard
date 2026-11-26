# Prüfprotokoll und Demo

Die Abnahme prüft die vier Messziele aus dem Projektantrag V2.1 und die vollständige Bedienung im Dashboard. Für jedes verwendete Testergebnis werden Commit, Betriebsmodus, Modell, Rechner, Testdatensatz und Datum festgehalten. Die Detailberichte der Skripte liegen unter `data/laufzeit/auswertung/`.

## Abnahmekriterien

| Messziel | Bestehenskriterium | Nachweis |
|---|---|---|
| Ticketpriorität | Mindestens 16 der 20 neuen Prüftickets haben die erwartete Priorität (80 %). Die Oberfläche zeigt die Begründung. | `auswertung.py --vergleich` und manueller Blick ins Ticket |
| Kundendokumentation | Bei mindestens 80 % der vorbereiteten Fragen erscheint die erwartete Fundstelle mit Belegtext. | `auswertung_doku.py` |
| Ähnliche gelöste Fälle | Bei mindestens 80 % der Tickets mit passendem Fall erscheint das erwartete gelöste Ticket unter den ersten drei Vorschlägen. | `auswertung_rag.py --datensatz abnahme --vergleich` |
| Kein ähnlicher Fall | Bei mindestens 80 % der Tickets ohne passenden Fall meldet die Anwendung einen fehlenden Treffer und zeigt keinen erfundenen Lösungsvorschlag. | Dieselbe Fallsuche mit getrennt ausgewiesenen Fällen ohne Treffer |

Zur Funktionsprüfung gehören außerdem das Einlesen aus der Testdatenablage, die Zuordnung der Ergebnisse zum Ticket, Statuswechsel mit Ticketalter und SLA, der Vorrang manueller Prioritäten, das Wachstum der Wissensbasis nach einem Abschluss und der Passwortmanager-Verweis. Fehler beim Serveraufruf zählen bei einer echten Messung als fehlgeschlagener Prüffall.

## Lokale Funktionsprüfung

Im Repo-Hauptordner bei aktivierter Python-Umgebung ausführen.

```text
python -m unittest discover -s tests -v
node --test tests/test_dashboard.mjs
```

Node wird nur für die automatisierten Prüfungen der Oberfläche benötigt. Für die HTTP-Prüfung das Backend im Mock-Modus nach der [Startanleitung](../README.md#einrichtung) starten. Bei einem abweichenden Backend-Port `--port` angeben.

```text
python scripts/auswertung_doku.py
python scripts/auswertung.py --vergleich --mock
python scripts/auswertung_rag.py
```

| Lokaler Lauf am 23.11.2026 | Beobachtung |
|---|---|
| Doku-Suche über HTTP im Mock-Modus | 11/11 erwartete Fundstellen, 4/4 korrekt gemeldete fehlende Treffer und 2/2 automatische Ticketabfragen |
| Promptvergleich im Mock-Modus | Für beide Promptvarianten wurden Berichte mit allen 20 Fällen erstellt. Der Lauf verwendet Platzhalterantworten. |
| Fallsuche auf den Abnahmefällen im Mock-Modus | 3/6 Fälle mit erwarteter Referenz (50 %) und 6/6 Fälle ohne Referenz (100 %). Der neu geschlossene Fall erschien bei der Wachstumskontrolle. |
| Dashboard-Tests | 6/6 Tests bestanden, darunter SLA-Grenzwerte, Wartezeit und Reihenfolge in der Übersicht. |

Der Mock bestätigt die Bedienung und die Auswertungslogik. Die Fallsuche verwendet darin einen Wortvergleich.

## Entwicklungsnotizen vom Windows-Laptop (23.–24.11.2026)

Diese früheren Versuche mit Qwen dienten der Fehlersuche auf dem Schullaptop. Sie beziehen sich auf frühere Code- und Promptstände. In einzelnen Läufen haben Regeln Modellwerte überschrieben. Für T14 und T15 sowie die weitere Abnahme gilt Gemma 4 26B-A4B auf dem Mac Pro.

| Frühe Beobachtung | Ergebnis auf dem Schullaptop |
|---|---|
| Qwen2.5 0.5B, zwei damalige Promptvarianten | 6/20 bzw. 5/20 richtige Prioritäten. |
| Qwen3 4B, damalige Kombination aus Modell und Regeln | 13/20 auf den Entwicklungsfällen, 8/12 auf zurückgehaltenen Kontrollfällen. |
| Ticketberatung, acht neue Beispiele | Drei Modellantworten und ein Prüfschritt aus einer Fachnotiz erfüllten die festgelegten Kriterien. Eine unbrauchbare Antwort wiederholte einen bereits abgeschlossenen Test. |
| Spamprüfung | Die Postfachwarnung #1021 war ein Fehlalarm, die Tonerwerbung #1010 wurde übersehen. Beide bleiben als Gegenprobe für den Modelllauf erhalten. |

## Messlauf auf dem Mac Pro

### Ergebnis der Fallsuche

Marlon hat die Ergebnisse am 25.11.2026 nach der Überarbeitung in #14 bis #16 gemeldet. Für die Wahl der Schwelle lief `scripts/auswertung_rag.py --nur-suche` mit dem Embedding-Dienst. Im vollständigen Abnahmelauf wertete zusätzlich Gemma 4 26B die gefundenen Fälle aus. [Messbericht in Issue #19](https://github.com/terror-4O4/lf12-helpdesk-dashboard/issues/19)

| Datensatz und Modus | Schwelle 0,65 | Schwelle 0,75 |
|---|---|---|
| Entwicklung, nur Suche (16 Tickets) | Bei 5 von 10 Tickets ohne Referenz erschien fälschlich ein früherer Fall. | 15/16 richtig. Das Skript empfahl diese Schwelle. |
| Abnahme, nur Suche (12 Tickets) | 7/12 richtig | 12/12 richtig |

Im vollständigen Abnahmelauf mit **0,75** verwies die Lösung bei **6/6** Tickets mit Referenz auf den erwarteten früheren Fall. Bei **6/6** Tickets ohne Referenz meldete das System korrekt, dass kein passender Fall vorliegt. Damit erreichte die Fallsuche in beiden Gruppen das Ziel von mindestens 80 %.

### Messlauf wiederholen

1. Gemma 4 26B-A4B über `LLAMA_URL` und `LLAMA_MODEL` sowie den lokalen Embedding-Dienst einrichten. In der lokalen `.env` für den gemessenen Stand `KI_MOCK=false` und `RAG_SCHWELLE=0.75` setzen und das Backend neu starten. `/api/status` zeigt den Betriebsmodus sowie die Erreichbarkeit beider Dienste. Den verwendeten Commit und die Modellnamen mit den Berichten festhalten.
2. Die für die Abgabe bestimmten Testfälle und Sollwerte vor dem Lauf festschreiben. Schwellenwerte und Prompts anhand von Entwicklungsfällen festlegen. Die Abnahmefälle dienen anschließend als unabhängiger Vergleich.
3. Im selben Setup die drei Auswertungen ausführen.

   ```text
   python scripts/auswertung.py --vergleich
   python scripts/auswertung_rag.py --datensatz abnahme --vergleich
   python scripts/auswertung_doku.py
   ```

4. Berichte dem Testprotokoll zuordnen und die vier Quoten samt Zähler und Nenner, typische Fehlzuordnungen und die Performancemessung übernehmen. Die Ergebnisse der beiden Testbedingungen getrennt ausweisen. Ein fehlendes Messergebnis als offen kennzeichnen.

Der Promptvergleich hält Modell, Testtickets und Hardware konstant. Ein einfacher Ausgangsprompt läuft auf 20 neuen Prüftickets gegen den gemeinsam festgelegten Analyse-Prompt v2 (SHA-256-Präfix `bed41d8163d7`). Welche Variante zuerst ausgeführt wird, wechselt pro Ticket. Beim zweiten Vergleich bearbeitet dasselbe Modell dieselben Fälle ohne und mit Ticket-Historie. Temperatur und Ausgabelimit von 256 Tokens sind für beide Varianten gleich. Die Quellenquote wird für die Variante mit Zugriff auf die Ticket-Historie ausgewertet. Antworten ohne Historie werden fachlich gesichtet. LoRA ist laut V2.1 optional.

Die Zeit bis zum ersten Token bezeichnet die Zeit vom Absenden der Anfrage an llama.cpp bis zum ersten empfangenen Ereignis mit erzeugtem Inhalt. Gibt der Server Denktext im Stream aus, zählt auch dieser. Die vollständige Antwortzeit reicht bis zum Ende der Antwort. Die Auswertung erfasst außerdem die Ausgabegeschwindigkeit in Tokens pro Sekunde. Aufwärmzeit und Messläufe getrennt dokumentieren.

## Demo im Dashboard

Für die Vorführung eine eigene Arbeitskopie der fiktiven Tickets nutzen. [Dashboard mit fixer Demo-Zeit](http://127.0.0.1:8000/?jetzt=2026-11-19T11:30) öffnen. Ein Reset über `POST /api/testdaten/zuruecksetzen` ersetzt die Ticket-Arbeitskopie durch den Testdatenstand und ist für eine isolierte Demo vorgesehen.

| Schritt | Vorführung | Erwartetes Verhalten |
|---|---|---|
| 1 | Übersicht öffnen und die Fahrzeugannahme im Ticket **#1007** zeigen. KI-Bewertung auslösen. | Neue Tickets und Kundenantworten stehen im Abschnitt „Handlungsbedarf“. Die SLA-Ampel reagiert auf Wartezeit und Priorität. Das Ticket enthält den KI-Vorschlag mit Begründung. |
| 2 | Für **#1026** einen Lösungsvorschlag anfordern. | Der erwartete ähnliche Fall **#1004** zum VPN erscheint als Ticketverweis. |
| 3 | In **#1004** die automatisch gefundenen Dokuabschnitte ansehen. Im Assistenten für den Kunden **Bau** nach dem Netzwerk-Gateway fragen. | Der Abschnitt **Netzwerk und Firewall** liefert einen Beleg mit Fundstelle. Eine Nachfrage nach dem Server-Admin-Passwort zeigt den zugehörigen Passwortmanager-Verweis. |
| 4 | In **#1023** den Wunsch nach einem zweiten Monitor als Fall ohne passende Historie prüfen. | Die Anwendung meldet „kein passender Fall“. |
| 5 | Ein eigenes fiktives Ticket mit Ursache und Lösungsweg schließen und einen entsprechend formulierten Folgefall öffnen. | Der gerade gelöste Fall gehört bei der nächsten Suche zur Wissensbasis. |

Vor der Präsentation den Ablauf einmal mit der verwendeten Modellkonfiguration durchgehen. Die im Demoablauf gezeigten Einzelfälle ergänzen die Auswertung auf dem festgelegten Testdatensatz.
