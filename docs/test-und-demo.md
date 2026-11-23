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

Der Mock bestätigt die Bedienung und die Auswertungslogik. Die Fallsuche verwendet darin einen Wortvergleich. Die Qualitäts- und Leistungswerte der echten Modelle auf dem Mac Pro stehen aus.

## Modellprobelauf unter Windows

Am 23.11.2026 lief llama.cpp Build b12651 auf einem Intel Core i7-1165G7 mit vier CPU-Threads pro Dienst. Für den Chat lief Qwen2.5 0.5B Instruct in Q4_K_M und für die Fallsuche EmbeddingGemma 300M in Q4_0. Die Messung prüft den technischen Ablauf und die Eignung dieser Entwicklungskonfiguration. Die Abnahme auf dem vorgesehenen Mac Pro erfolgt separat. [llama.cpp](https://github.com/ggml-org/llama.cpp/releases/tag/b12651) · [Chat-Modell](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF) · [Embedding-Modell](https://huggingface.co/ggml-org/embeddinggemma-300M-qat-q4_0-GGUF)

| Prüfung | Beobachtung unter Windows |
|---|---|
| Priorisierung mit einfachem Prompt | 6/20 richtige Prioritäten (30 %), im Mittel 0,945 s bis zum ersten Token, 3,370 s Antwortzeit, 39,2 Tokens/s |
| Priorisierung mit angepasstem Prompt | 5/20 richtige Prioritäten (25 %), im Mittel 4,587 s bis zum ersten Token, 6,793 s Antwortzeit, 35,4 Tokens/s |
| Kundendoku nach Überarbeitung der Belegauswahl | 9/11 richtige Fundstellen (82 %), 4/4 korrekte Meldungen ohne Treffer und 2/2 automatische Ticketabfragen. Im ersten Lauf waren 5/11 Fundstellen richtig. Beide Läufe verwendeten dieselben Fälle. |
| Ähnliche Fälle nach Überarbeitung der Quellenauswahl | 6/6 passende Referenzen in den ersten drei Vorschlägen (100 %), 5/6 Fälle ohne Referenz korrekt als fehlender Treffer behandelt (83 %). Die Wachstumskontrolle bestand. |

Das kleine Chat-Modell bleibt bei beiden Priorisierungsvarianten unter dem Ziel von 80 %. Der längere Prompt erhöhte in dieser Konfiguration die Zeit bis zum ersten Token. Für den Mac Pro sollte die Modellauswahl anhand der Auswertung auf Entwicklungsfällen erfolgen. Die Abnahmefälle dienen anschließend der Messung des gewählten Stands.

Bei der ersten Fallauswertung lehnte die KI passende historische Belege ab. Das Backend übernimmt nun die gespeicherten Ursachen und Lösungswege der vom Modell gewählten Tickets. Für den Wiederholungslauf ergab die Kalibrierung auf den Entwicklungsfällen eine Ähnlichkeitsschwelle von 0,76. Die zwölf Abnahmefälle blieben beim Wiederholungslauf gleich. Ein externer Bildschirm ohne Signal wurde fälschlich mit einem früheren Notebook-Ausfall verknüpft. Der Bericht enthält auch die Antworten ohne Ticket-Historie für alle zwölf Fälle.

## Gegenprobe zur Spam-Prüfung und Ticketbewertung

Im ersten Dashboard-Durchlauf landeten die Outlook-Warnung #1021 und der Umzug #1030 in der Spam-Prüfung. Die Werbung #1010 erschien als Software. Für den Monitorwunsch #1023 übernahm die KI Rückrufzeiten aus der Kundenakte als Begründung. Das Dashboard prüft den Eingang jetzt automatisch. Freigegebene Tickets erhalten eine Bewertung mit Ticketbeleg und Herkunft für Kategorie und Priorität.

Die beiden folgenden Läufe nutzten am 23.11.2026 das lokale Windows-Modell Qwen2.5 0.5B und dieselbe Verarbeitungslogik. Die erste Serie umfasst die bekannten Demofälle. Für die zweite Serie durchliefen die 20 unveränderten Tickets aus `tickets_promptvergleich.json` die Produktions-API in einer eigenen temporären Arbeitskopie. Die ausgewiesene Zahl bei Kategorie und Priorität bezieht sich jeweils auf reguläre Supportanfragen.

| Prüfung | 34 Demotickets | 20 separate Prüftickets |
|---|---|---|
| Spam erkannt | 4/4 | 0/1 |
| Reguläre Anfragen durchgelassen | 30/30 | 19/19 |
| Kategorie richtig | 30/30 | 11/19 |
| Priorität richtig | 23/30 | 10/19 |

Im zweiten Lauf gelangte ein Angebot für einen kostenpflichtigen Firmeneintrag in den Support. Der Ausfall eines gemeinsamen Portals wurde als Hardwareproblem mit niedriger Priorität eingestuft. Der eine Werbefall der Serie reicht für eine allgemeine Schätzung der Spam-Erkennungsrate nicht aus. Bei #1002 steht im Entwicklungsdatensatz ein fachlicher Widerspruch: Die Kundenakte nennt für den Lagerdrucker die Stufe „hoch“, der Sollwert lautet „sehr_hoch“. Die Auswertung zählt die Abweichung mit.

Der Demo-Lauf lässt sich mit `python scripts/auswertung_eingang.py` wiederholen. Für die Vorführung eignen sich die gegensätzlichen Postfachmeldungen #1003 und #1021 sowie der Monitorwunsch #1023. Die Spam-Prüfung bietet Freigabe und Bestätigung. Am regulären Ticket kann der Support über „Nachrichtenaktionen“ eine übersehene Werbenachricht markieren.

## Messlauf auf dem Mac Pro

1. Die autorisierte Umgebung mit Chat- und Embedding-Dienst einrichten, `KI_MOCK=false` setzen und das Backend neu starten. `/api/status` zeigt den Betriebsmodus sowie die Erreichbarkeit beider Dienste. Den verwendeten Commit und die Modellnamen mit den Berichten festhalten.
2. Die für die Abgabe bestimmten Testfälle und Sollwerte vor dem Lauf festschreiben. Schwellenwerte und Prompts anhand von Entwicklungsfällen festlegen. Die Abnahmefälle dienen anschließend als unabhängiger Vergleich.
3. Im selben Setup die drei Auswertungen ausführen.

   ```text
   python scripts/auswertung.py --vergleich
   python scripts/auswertung_rag.py --datensatz abnahme --vergleich
   python scripts/auswertung_doku.py
   ```

4. Berichte dem Testprotokoll zuordnen und die vier Quoten samt Zähler und Nenner, typische Fehlzuordnungen und die Performancemessung übernehmen. Die Ergebnisse der beiden Testbedingungen getrennt ausweisen. Ein fehlendes Messergebnis als offen kennzeichnen.

Der Promptvergleich hält Modell, Testtickets und Hardware konstant. Ein einfacher Ausgangsprompt läuft auf 20 neuen Prüftickets gegen den um Regeln und Beispiele erweiterten Prompt. Welche Variante zuerst ausgeführt wird, wechselt pro Ticket. Beim zweiten Vergleich bearbeitet dasselbe Modell dieselben Fälle ohne und mit Ticket-Historie. Temperatur und Ausgabelimit von 256 Tokens sind für beide Varianten gleich. Die Quellenquote wird für die Variante mit Zugriff auf die Ticket-Historie ausgewertet. Antworten ohne Historie werden fachlich gesichtet. LoRA ist laut V2.1 optional.

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
