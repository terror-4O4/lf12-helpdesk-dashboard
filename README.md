# LF12 · Helpdesk-Dashboard mit KI-Assistent

Das Helpdesk-Dashboard für Lernfeld 12 (Klasse 12BE15) zeigt offene Tickets, Wartezeiten und Handlungsbedarf. Ein lokal betriebenes Sprachmodell mit llama.cpp schlägt Prioritäten vor und nutzt ähnliche gelöste Tickets für mögliche Lösungswege. Im Dashboard lässt sich die Kundendokumentation zum Ticket oder per freier Frage durchsuchen. Bei der Bearbeitung entscheidet der Support.

Grundlage ist der **Projektantrag V2.1**. Die [Projektdokumentation](docs/README.md) beschreibt den Aufbau und die Projektgrenzen. Der [Prüf- und Demoablauf](docs/test-und-demo.md) enthält Messziele, Auswertung und Präsentationsfälle.

> **Alle Daten in diesem Repo sind frei erfunden.** Es gibt keine echten Kunden, Tickets, Personen oder Zugangsdaten.

## Team

| Name | Rolle |
|---|---|
| Marlon G. | Server, Bereitstellung, Code-Review |
| Linus R. | |
| Ricardo H. | |
| Jennan H. | |

## Architektur

```
Browser (Dashboard)  ──►  FastAPI  ──►  llama-server (Chat und Klassifikation)
                             ├────────►  zweiter llama-server (Embeddings für ähnliche Fälle)
                             └────────►  Ticket-Arbeitskopie, fiktive Kundendoku
```

- **Entwicklung:** jeder auf dem eigenen Laptop (Windows oder macOS)
- **Betrieb:** Gemma 4 26B-A4B über llama.cpp auf dem Mac Pro, Zugriff für die Gruppe nur über Tailscale auf Weboberfläche und API
- **Deployment:** ausschließlich durch Marlon, nur geprüfter Code aus `main`

## Ordnerstruktur

| Ordner | Inhalt |
|---|---|
| `backend/` | Python-Backend: holt Daten, baut Prompts, spricht mit llama-server |
| `frontend/` | Dashboard-Oberfläche (HTML, CSS, JavaScript) |
| `data/testdaten/` | Fiktive Tickets, Kundendoku, Spam-Beispiele |
| `docs/` | Projektdokumentation, Datenformat, Prüf- und Demoablauf |
| `scripts/` | Backend-Start, Auswertungen und Bereitstellung für den Mac Pro |
| `tests/` | Automatisierte Prüfungen für Backend und Dashboard |

## Einrichtung

### Voraussetzungen

- [Git](https://git-scm.com/downloads)
- **Python 3.11 oder neuer** (lokal mit 3.12 geprüft)
  - Windows: [python.org](https://www.python.org/downloads/), bei der Installation **„Add python.exe to PATH“** anhaken
  - macOS: `brew install python@3.13`. ⚠️ Das vorinstallierte `python3` von Apple ist 3.9 und zu alt. Die Umgebung daher mit `python3.13 -m venv .venv` anlegen
- Editor, z. B. [VS Code](https://code.visualstudio.com/)

### Repo klonen

```bash
git clone https://github.com/terror-4O4/lf12-helpdesk-dashboard.git
cd lf12-helpdesk-dashboard
```

### Konfiguration anlegen

Die Datei `.env.example` kopieren und als `.env` speichern. In `.env` stehen eure lokalen Einstellungen (Server-Adresse, API-Key).

```bash
# macOS / Linux
test -f .env || cp .env.example .env
```

```powershell
# Windows (PowerShell)
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

> ⚠️ Die `.env` wird **nie** committet (steht in `.gitignore`). Den API-Key für den Server bekommt ihr von Marlon persönlich, nicht über Trello, WhatsApp-Gruppe oder das Repo.

### Python-Umgebung

```bash
# macOS / Linux
python3.13 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

In der aktivierten Umgebung die Abhängigkeiten installieren.

```text
python -m pip install -r backend/requirements.txt
```

Die Vorlage startet mit `KI_MOCK=true`. Danach das Backend mit `./scripts/start-backend.sh` (macOS/Linux) oder `.\scripts\start-backend.ps1` (Windows) starten und [das Dashboard](http://127.0.0.1:8000/) öffnen. Die feste [Demo-Uhrzeit](http://127.0.0.1:8000/?jetzt=2026-11-19T11:30) passt zu den Beispieltickets. Für den Modellbetrieb die lokale Konfiguration nach der [Backend-Anleitung](backend/README.md) einrichten.

## Mitarbeiten

Kurzfassung, Details in [CONTRIBUTING.md](CONTRIBUTING.md):

1. Trello-Karte nehmen und nach **„In Arbeit“** schieben
2. Eigenen Branch anlegen, z. B. `feature/ki-textfeld`
3. Arbeiten, committen, pushen
4. Pull Request gegen `main` öffnen und Checkliste ausfüllen
5. Marlon prüft und mergt. **Direkt auf `main` pushen ist gesperrt.**

## Sicherheitsregeln

- Keine Passwörter, API-Keys oder Tokens ins Repo, auch nicht „nur kurz zum Testen“
- Keine echten Kundendaten, keine Daten aus Ausbildungsbetrieben
- Keine Modelldateien (`*.gguf`) committen, die sind mehrere GB groß
- Zugangsdaten in der Test-Kundendoku nur als Verweis („siehe Passwortmanager, Eintrag XY“)

## Termine

| Was | Wann |
|---|---|
| Abgabe Dateien | 11.12.2026 |
| Präsentation | spätestens 16.12.2026 |
