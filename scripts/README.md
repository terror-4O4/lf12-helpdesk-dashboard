# Skripte

Skripte für Windows als `.ps1`, für macOS/Linux als `.sh`.

| Skript | Wofür | Wo ausführen |
|---|---|---|
| `start-backend.sh` / `.ps1` | Backend starten | Entwickler-Rechner |
| `auswertung.py` | Trefferquote der KI-Ticket-Analyse messen, mehrere Modelle vergleichen | Rechner mit Backend und `.env` |
| `macpro/install-llama-dienst.sh` | llama-server als Dienst auf dem Mac Pro einrichten | Mac Pro, nur Marlon |

## auswertung.py

Lässt alle Testtickets von der KI bewerten und vergleicht mit `data/testdaten/erwartet.json`. Benutzt die Prompts und Prüfungen des Backends, die Testdaten bleiben unverändert.

```bash
source .venv/bin/activate
python scripts/auswertung.py                              # alle Modelle des llama-servers
python scripts/auswertung.py -m gemma-4-26B-A4B-it-Q4_0   # nur ein Modell
```

- Braucht in der `.env`: `LLAMA_URL`, `LLAMA_API_KEY` und bei Router-Modus `LLAMA_MODEL`
- Das Modell aus `LLAMA_MODEL` wird zuletzt getestet, damit es danach wieder geladen ist
- Ergebnis als Markdown-Tabelle (für das Testprotokoll) und JSON unter `data/laufzeit/auswertung/`
- Abbrechen mit Ctrl+C, bisherige Ergebnisse werden trotzdem ausgewertet
- Die Zeile "Analyse-Prompt (SHA-256)" zeigt, mit welcher Prompt-Version gemessen wurde (vorher/nachher vergleichen)

## macpro/install-llama-dienst.sh

Richtet llama-server als LaunchDaemon ein: startet beim Hochfahren als User `kiserver`, Router-Modus mit allen Modellen aus `/opt/ki-projekt/models`, immer nur ein Modell im VRAM, API-Key, nur LAN-IP, Neustart nach Absturz, Log mit Rotation.

```bash
sudo bash install-llama-dienst.sh               # einrichten oder aktualisieren
sudo bash install-llama-dienst.sh --status      # Zustand, Modelle, letzte Log-Zeilen
sudo bash install-llama-dienst.sh --entfernen   # Dienst entfernen (Modelle und Key bleiben)
```

| Datei | Inhalt |
|---|---|
| `/Library/LaunchDaemons/de.lf12.llama-server.plist` | Dienst-Definition |
| `/opt/ki-projekt/config/models.ini` | Einstellungen pro Modell (GPU, Kontext, Denkmodus) |
| `/opt/ki-projekt/config/api-key` | API-Key, nur für `kiserver` lesbar, nie ins Repo |
| `/opt/ki-projekt/logs/llama-server.log` | Log, wird ab 10 MB rotiert |

Neues Modell: `.gguf` nach `/opt/ki-projekt/models` legen und das Skript erneut ausführen. Anderes Standardmodell: `sudo STANDARD_MODELL=<name> bash install-llama-dienst.sh`.
