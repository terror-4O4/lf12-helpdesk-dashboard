# Backend

Python-Backend (FastAPI). Liefert Tickets, Kunden und Kundendoku aus `data/testdaten/` und leitet Fragen an die lokale KI weiter. **Es werden keine externen Dienste angesprochen**, auch die Testseite `/docs` funktioniert ohne Internet.

## Einmalig einrichten

Voraussetzung: `.env` und `.venv` wie im Haupt-README beschrieben. Dann im **Repo-Hauptordner** bei aktivierter `.venv`:

```bash
pip install -r backend/requirements.txt
```

## Starten

**macOS:**
```bash
./scripts/start-backend.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\start-backend.ps1
```

Danach im Browser:
- **http://127.0.0.1:8000/docs**: Testseite, auf der man jede Schnittstelle direkt ausprobieren kann („Try it out“)
- **http://127.0.0.1:8000/api/status**: Läuft das Backend, ist die KI erreichbar?

Beenden mit `Strg + C`.

## Schnittstellen

| Methode | Pfad | Liefert |
|---|---|---|
| GET | `/api/status` | Status von Backend und KI |
| GET | `/api/tickets` | Alle Tickets, Filter: `?status=neu`, `?kunde=bau` |
| GET | `/api/tickets/{id}` | Ein Ticket, z. B. `/api/tickets/1001` |
| POST | `/api/tickets` | Legt ein neues Ticket an: `{"kunde": "bau", "titel": "...", "beschreibung": "..."}`, Nummer wird automatisch vergeben |
| PATCH | `/api/tickets/{id}` | Ändert nur die mitgeschickten Felder: `status`, `prioritaet` (gilt dann als manuell), `zugewiesen_an`, `loesungsweg`, `spam_entscheidung`. Schließen nur mit Lösungsweg oder bestätigtem Spam |
| GET | `/api/kunden` | Alle Kunden |
| GET | `/api/kunden/{kunde}/doku` | Kundendoku als Markdown |
| GET | `/api/tickets/{id}/doku` | Passende Abschnitte aus der Doku des Ticketkunden |
| POST | `/api/kunden/{kunde}/doku/suche` | Antwort auf `{"frage": "..."}` mit Belegtext, Fundstelle und hinterlegten Portal-Links |
| POST | `/api/tickets/{id}/frage` | Ordnet eine Störungsmeldung oder Rückfrage anhand von Kundenakte, Fallhistorie und lokalem Fachwissen ein. Für Folgefragen kann `verlauf` die letzten sechs Benutzernachrichten desselben Tickets in zeitlicher Reihenfolge enthalten. |
| POST | `/api/ki/frage` | Beantwortet allgemeine IT-Fragen mit lokalem Fachwissen. Kundenakten und frühere Kundentickets sind nur im Ticketkontext verfügbar. |
| POST | `/api/tickets/{id}/analyse` | Lässt das Projektmodell Spam, Kategorie und Priorität in einer gemeinsamen Analyse bewerten. Mit `?speichern=false` nur anzeigen |
| GET | `/api/tickets/{id}/aehnliche` | Nur die Suche: ähnlichste gelöste Tickets mit Ähnlichkeit. `?ohne_schwelle=true&anzahl=10` zeigt auch Fälle unter der Schwelle |
| POST | `/api/tickets/{id}/loesungsvorschlag` | Suche plus KI: bis zu 3 Ursachen mit Lösungsweg und Verweis auf die Tickets, oder „kein passender Fall“. `?speichern=false` = nur anzeigen |
| GET | `/api/wissensbasis` | Anzahl der gelösten Tickets in der Wissensbasis, Schwelle, Modell |
| POST | `/api/wissen/wikipedia` | Beantwortet allgemeine IT-Begriffsfragen aus den lokalen Fachnotizen und liefert die jeweilige Originalquelle. |
| POST | `/api/testdaten/zuruecksetzen` | Verwirft alle Änderungen und lädt die Testtickets neu |
| POST | `/api/testdaten/ergaenzen` | Ergänzt fehlende Übungstickets und liefert die neu angelegten Ticketnummern |

Das Backend arbeitet mit einer Arbeitskopie der Tickets in `data/laufzeit/` (nicht im Repo). Details in [`docs/datenformat.md`](../docs/datenformat.md#testdaten-und-arbeitskopie).

Spam, Kategorie, Priorität und Begründung kommen im Modellbetrieb aus einer Antwort von llama.cpp. Die Auswertung verwendet dafür dieselbe Analysefunktion wie das Dashboard. Die Spam-Warteschlange folgt dem Modellverdacht oder der ausdrücklichen Mitarbeiterentscheidung. Regelhinweise stehen separat am Ticket. Eine erneute Bewertung erhält die manuell gesetzte Priorität und die Spam-Entscheidung.

Bei Spam-Entscheidungen sendet das Dashboard den angezeigten Stand mit (`erwartete_spam_entscheidung`, `erwarteter_status`). Hat eine zweite Person inzwischen entschieden, liefert PATCH HTTP 409. Das Dashboard lädt dann den aktuellen Stand.

Für die Ticket-Arbeitskopie ist ein Uvicorn-Worker vorgesehen. Manuelle und KI-Änderungen werden beim Speichern zusammengeführt. Hat sich bei der Berechnung die entscheidende Ticket- oder Fallgrundlage geändert, meldet die API einen Konflikt (`409`) und der Vorgang kann erneut ausgeführt werden.

## KI: Mock oder echt

In der `.env`:

| Einstellung | Wirkung |
|---|---|
| `KI_MOCK=true` | Beispielantworten, **kein KI-Server nötig**. Zum Entwickeln am Frontend |
| `KI_MOCK=false` | Echte Antworten vom llama-server unter `LLAMA_URL` |

Nach einer Änderung an der `.env` das Backend neu starten.

## Suche in der Kundendoku

Die Ticketansicht sucht nach Begriffen in Titel und Beschreibung. Freie Doku-Fragen
beziehen sich auf den im Assistenten gewählten Kunden. Das Backend stellt dafür bis
zu drei Abschnitte aus dessen Datei zusammen. Im echten Modus wählt llama.cpp daraus
die Fundstelle oder meldet, dass kein Abschnitt die Antwort belegt. Im Mock-Modus
zeigt die Anwendung den besten Worttreffer. Belegtext und Portal-Links stammen aus
der Markdown-Datei. Antworten auf Passwortfragen verwenden die hinterlegten
Passwortmanager-Verweise.

## Fachwissen in der Ticketberatung

Die Anwendung sucht automatisch nach passenden [lokalen Fachnotizen](../data/wissen/wikipedia.json). Zu den Quellen gehören Wikipedia, das gematik-Fachportal und Herstellerdokumentation. Die Ticketberatung verbindet diese Hinweise mit dem betroffenen System und früheren Fällen des Kunden. Die Quellen lassen sich nach der Antwort aufklappen. Die Suche funktioniert offline. Für die verlinkten Originalartikel wird Internetzugang benötigt. Die Wikipedia-Begriffsnotizen stehen unter CC BY-SA 4.0. [Herkunft und Lizenzen](../data/wissen/README.md)

Standardmäßig beantwortet der unter `LLAMA_URL` konfigurierte Dienst auch die Beratungsfragen. Wer für die Formulierung ein zweites lokales Chatmodell betreibt, kann dessen Adresse in `BERATUNG_URL` und bei Bedarf den Modellnamen in `BERATUNG_MODEL` eintragen. `/api/status?modelldetails=true` zeigt die erreichbaren Dienste und die vom Server gemeldeten Modelldateien.

Auf dem Mac Pro läuft Gemma 4 26B-A4B. Der Router verwendet den Modellnamen `gemma-4-26B-A4B-it-Q4_0` in `LLAMA_MODEL`. Für diesen Betrieb bleiben `BERATUNG_URL` und `BERATUNG_MODEL` leer.

## Ähnliche Tickets (RAG)

1. **Wissensbasis:** alle geschlossenen Tickets mit Lösungsweg (ohne Spam). Für jedes wird einmal ein Embedding berechnet (Zahlenvektor, der die Bedeutung abbildet) und in `data/laufzeit/wissensbasis.json` gespeichert. Neu geschlossene Tickets kommen beim nächsten Suchen automatisch dazu.
2. **Suche:** Das neue Ticket bekommt ebenfalls einen Vektor und wird mit allen Fällen verglichen (Kosinus-Ähnlichkeit, 0 bis 1). Fälle beim selben Kunden bekommen `RAG_KUNDENBONUS` dazu. Nur Fälle ab `RAG_SCHWELLE` zählen, höchstens 3.
3. **Kein Fall über der Schwelle:** Antwort „kein passender Fall“, die Chat-KI wird gar nicht gefragt. So kann sie auch nichts erfinden.
4. **Sonst:** Die Chat-KI wählt bis zu drei passende Fallnummern aus den gefundenen Tickets oder gibt eine leere Liste zurück. Das Backend prüft die Nummern und übernimmt Ursachen und Lösungswege aus den ausgewählten Fällen.

| Einstellung (.env) | Bedeutung |
|---|---|
| `EMBED_URL` | Embedding-Server, eigener llama-server mit EmbeddingGemma 300M (auf dem Mac Pro Port 8081, CPU). Gleicher API-Key wie `LLAMA_API_KEY` |
| `RAG_SCHWELLE` | Ab welcher Ähnlichkeit ein Fall passt. Empfehlung liefert `scripts/auswertung_rag.py --nur-suche` |
| `RAG_KUNDENBONUS` | Bonus für denselben Kunden, Standard 0.05 |

Mit `KI_MOCK=true` vergleicht der Mock einfach gleiche Wörter und übernimmt Ursache und Lösung der gefundenen Tickets direkt. Das reicht zum Entwickeln, ersetzt aber keinen Test mit dem echten Modell.

Eine Vektordatenbank (Qdrant, Chroma) ist bewusst nicht dabei: Bei einigen Dutzend Tickets dauert der Vergleich in Python unter einer Millisekunde, und es gibt einen Dienst weniger.

## Sperre: Daten bleiben im lokalen Netz

Beim Start prüft das Backend `LLAMA_URL`, `EMBED_URL` und die optionale `BERATUNG_URL`. Erlaubt sind **nur**:
- dieser Rechner (`127.0.0.1`, `localhost`)
- private Netze (`10.x.x.x`, `172.16.x.x` bis `172.31.x.x`, `192.168.x.x`)

Zeigt eine der Adressen auf etwas anderes, z. B. einen KI-Dienst im Internet, **startet das Backend nicht** und meldet `ABBRUCH: ...`. Das gilt auch bei `KI_MOCK=true`. Außerdem ignoriert das Backend Proxy-Einstellungen des Systems und spricht den llama-server immer direkt an.

Diese Sperre darf nur nach Absprache mit Marlon geändert werden.
