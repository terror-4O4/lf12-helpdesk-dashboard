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
| POST | `/api/ki/frage` | Antwort der KI auf `{"frage": "..."}` |
| POST | `/api/tickets/{id}/analyse` | KI bewertet das Ticket: Priorität, Spam, Kategorie, Begründung. Mit `?speichern=false` nur anzeigen, nicht speichern |
| POST | `/api/testdaten/zuruecksetzen` | Verwirft alle Änderungen und lädt die Testtickets neu |

Das Backend arbeitet mit einer Arbeitskopie der Tickets in `data/laufzeit/` (nicht im Repo). Details in [`docs/datenformat.md`](../docs/datenformat.md#testdaten-und-arbeitskopie).

Das Datenformat steht in [`docs/datenformat.md`](../docs/datenformat.md).

## KI: Mock oder echt

In der `.env`:

| Einstellung | Wirkung |
|---|---|
| `KI_MOCK=true` | Beispielantworten, **kein KI-Server nötig**. Zum Entwickeln am Frontend |
| `KI_MOCK=false` | Echte Antworten vom llama-server unter `LLAMA_URL` |

Nach einer Änderung an der `.env` das Backend neu starten.

## Sperre: Daten bleiben im lokalen Netz

Beim Start prüft das Backend `LLAMA_URL`. Erlaubt sind **nur**:
- dieser Rechner (`127.0.0.1`, `localhost`)
- private Netze (`10.x.x.x`, `172.16.x.x` bis `172.31.x.x`, `192.168.x.x`)

Zeigt `LLAMA_URL` auf etwas anderes, z. B. einen KI-Dienst im Internet, **startet das Backend nicht** und meldet `ABBRUCH: ...`. Das gilt auch bei `KI_MOCK=true`. Außerdem ignoriert das Backend Proxy-Einstellungen des Systems und spricht den llama-server immer direkt an.

Diese Sperre darf nur nach Absprache mit Marlon geändert werden.
