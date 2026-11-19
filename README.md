# LF12 · Helpdesk-Dashboard mit KI-Assistent

Schulprojekt im Lernfeld 12 (Klasse 12BE15): ein Dashboard für den IT-Support, das den Zustand aller Tickets auf einen Blick zeigt. Eine **lokal laufende KI** (llama.cpp) priorisiert Tickets, erkennt Spam und schlägt anhand bereits gelöster Tickets mögliche Ursachen und Lösungswege vor. Kundendokumentation lässt sich über ein KI-Textfeld durchsuchen.

Verbindliche Grundlage ist der genehmigte **Projektantrag V2.1**.

> **Alle Daten in diesem Repo sind frei erfunden.** Es gibt keine echten Kunden, Tickets, Personen oder Zugangsdaten.

## Team

| Name | Rolle |
|---|---|
| Marlon G. | Server, Bereitstellung, Code-Review |
| Linus R. | Gar nichts |
| Ricardo H. | Keine Ahnung |
| Jennan H. | rauchen |

## Architektur (Kurzfassung)

```
Browser (Dashboard)  ──►  Backend (Python)  ──►  llama-server (llama.cpp, OpenAI-kompatible API)
                              │
                              └──►  Testdaten (fiktive Tickets, Kundendoku)
```

- **Entwicklung:** jeder auf dem eigenen Laptop (Windows oder macOS)
- **Betrieb:** Mac Pro als Server, Zugriff für die Gruppe nur über Tailscale auf Weboberfläche und API
- **Deployment:** ausschließlich durch Marlon, nur geprüfter Code aus `main`

## Ordnerstruktur

| Ordner | Inhalt |
|---|---|
| `backend/` | Python-Backend: holt Daten, baut Prompts, spricht mit llama-server |
| `frontend/` | Dashboard-Oberfläche (HTML, CSS, JavaScript) |
| `data/testdaten/` | Fiktive Tickets, Kundendoku, Spam-Beispiele |
| `docs/` | Projektdokumentation, Testprotokolle, Diagramme |
| `scripts/` | Hilfsskripte (Server starten, Testdaten erzeugen, ...) |

## Einrichtung

### Voraussetzungen

- [Git](https://git-scm.com/downloads)
- [Python 3.11 oder neuer](https://www.python.org/downloads/) (unter Windows bei der Installation **„Add python.exe to PATH“** anhaken)
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
cp .env.example .env
```

```powershell
# Windows (PowerShell)
Copy-Item .env.example .env
```

> ⚠️ Die `.env` wird **nie** committet (steht in `.gitignore`). Den API-Key für den Server bekommt ihr von Marlon persönlich, nicht über Trello, WhatsApp-Gruppe oder das Repo.

### Python-Umgebung

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Abhängigkeiten werden ergänzt, sobald das Backend steht (`backend/requirements.txt`).

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
