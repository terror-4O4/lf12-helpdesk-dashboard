# Skripte

Skripte für Windows als `.ps1`, für macOS/Linux als `.sh`.

| Skript | Wofür | Wo ausführen |
|---|---|---|
| `start-backend.sh` / `.ps1` | Backend starten | Entwickler-Rechner |
| `auswertung.py` | Trefferquote der KI-Ticket-Analyse messen, mehrere Modelle vergleichen | Rechner mit Backend und `.env` |
| `auswertung_rag.py` | Ähnliche Tickets (RAG) gegen die Messziele prüfen, Schwelle bestimmen | Rechner mit Backend und `.env` |
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

## auswertung_rag.py

Prüft die Lösungsvorschläge aus ähnlichen Tickets gegen die Messziele aus dem Antrag (je 80 %): Der passende Fall steht unter den Top 3, und ohne passenden Fall erfindet die KI nichts. Welcher Fall passt, steht in `data/testdaten/erwartet.json` im Feld `aehnlich`.

```bash
source .venv/bin/activate
python scripts/auswertung_rag.py --nur-suche   # nur Suche, schnell, mit Empfehlung für RAG_SCHWELLE
python scripts/auswertung_rag.py               # Suche plus Chat-KI
python scripts/auswertung_rag.py --vergleich   # zusätzlich Vorschläge ohne Ticket-Historie (Test "ohne/mit Training")
```

- Braucht in der `.env` zusätzlich `EMBED_URL`
- Prüft außerdem, ob ein frisch geschlossenes Ticket beim nächsten ähnlichen Fall gefunden wird (Wissensbasis wächst)
- Nutzt die Testdaten und eine eigene Vektor-Datei, das Dashboard bleibt unverändert
- Ergebnis als Markdown und JSON unter `data/laufzeit/auswertung/rag_*`

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
| `/Library/LaunchDaemons/de.lf12.llama-embed.plist` | Embedding-Dienst (nur wenn ein Modell in `models-embedding` liegt) |
| `/opt/ki-projekt/models-embedding/` | Embedding-Modell, bewusst getrennt von `models`, sonst erscheint es im Router-Modus als Chat-Modell |
| `/opt/ki-projekt/logs/llama-embed.log` | Log des Embedding-Dienstes |

**Embedding-Dienst:** Liegt genau eine `.gguf` in `/opt/ki-projekt/models-embedding`, richtet das Skript einen zweiten Dienst `de.lf12.llama-embed` auf Port 8081 ein. Er läuft nur auf der CPU (`--device none`), damit der VRAM dem Chat-Modell bleibt, mit demselben API-Key. Ein eigener Dienst ist nötig, weil der Router-Modus nur ein Modell gleichzeitig hält und sonst bei jeder Suche das Chat-Modell entladen würde.

Neues Modell: `.gguf` nach `/opt/ki-projekt/models` legen und das Skript erneut ausführen. Anderes Standardmodell: `sudo STANDARD_MODELL=<name> bash install-llama-dienst.sh`.
