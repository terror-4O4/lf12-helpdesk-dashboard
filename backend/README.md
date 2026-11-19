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
| GET | `/api/kunden` | Alle Kunden |
| GET | `/api/kunden/{kunde}/doku` | Kundendoku als Markdown |
| POST | `/api/ki/frage` | Antwort der KI auf `{"frage": "..."}` |

Das Datenformat steht in [`docs/datenformat.md`](../docs/datenformat.md).

## KI: Mock oder echt

In der `.env`:

| Einstellung | Wirkung |
|---|---|
| `KI_MOCK=true` | Beispielantworten, **kein KI-Server nötig**. Zum Entwickeln am Frontend |
| `KI_MOCK=false` | Echte Antworten vom llama-server unter `LLAMA_URL` |

Nach einer Änderung an der `.env` das Backend neu starten.
