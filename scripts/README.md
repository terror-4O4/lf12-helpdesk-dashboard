# Skripte

Skripte für Windows als `.ps1`, für macOS/Linux als `.sh`.

| Skript | Wofür | Wo ausführen |
|---|---|---|
| `start-backend.sh` / `.ps1` | Backend starten | Entwickler-Rechner |
| `auswertung.py` | Ticketpriorisierung und Laufzeit messen, Modell- oder Promptvergleich | Rechner mit lokalem Chat-Dienst |
| `auswertung_rag.py` | Ähnliche Tickets mit und ohne Historie prüfen, Suchschwelle bestimmen | Rechner mit lokalem Chat- und Embedding-Dienst oder Mock |
| `auswertung_doku.py` | Fundstellen, fehlende Treffer und Ticketbezug der Kundendoku-Suche prüfen | Rechner mit laufendem Backend |
| `macpro/install-llama-dienst.sh` | llama-server als Dienst auf dem Mac Pro einrichten | Mac Pro, nur Marlon |

## auswertung.py

Der Standardlauf vergleicht KI-Bewertungen mit `data/testdaten/erwartet.json`. Für die Abnahme lässt `--vergleich` den einfachen und angepassten Prompt auf denselben 20 neuen Prüftickets aus `data/testdaten/tickets_promptvergleich.json` laufen. Pro Priorität gibt es fünf Fälle.

```bash
source .venv/bin/activate
python scripts/auswertung.py                    # Modellvergleich auf Entwicklungsdaten
python scripts/auswertung.py --vergleich        # Promptvergleich auf Abnahmedaten
python scripts/auswertung.py --vergleich --mock # Auswertungsablauf mit Platzhaltern
```

- Für den echten Lauf `LLAMA_URL`, gegebenenfalls `LLAMA_API_KEY` und im Router-Modus das verwendete Modell konfigurieren.
- Für den Modellvergleich lassen sich Modelle mit `-m` auswählen. Der Promptvergleich nutzt standardmäßig `LLAMA_MODEL` oder das Standardmodell des Servers. Je Vergleichspaar bleibt das Modell gleich.
- Die Promptberichte `data/laufzeit/auswertung/promptvergleich-*.md` und `*.json` enthalten Trefferquoten, Fehlzuordnungen, Prompt-Versionen und Laufzeiten. Bei echtem Modellbetrieb wird die erste Ausgabe im Stream des Chat-Diensts gemessen. Der Mock prüft den Auswertungsablauf mit Platzhaltern.

## auswertung_rag.py

Prüft, ob bei einem bekannten Treffer die erwartete Ticketnummer unter den ersten drei Vorschlägen erscheint. Bei Fällen ohne Treffer prüft die Auswertung, ob die Antwort das kenntlich macht. Beide Quoten haben im Projektantrag ein Ziel von 80 %.

```bash
source .venv/bin/activate
python scripts/auswertung_rag.py --nur-suche                    # Suche und Schwellenwert auf Entwicklungsdaten
python scripts/auswertung_rag.py --datensatz abnahme --vergleich # Suche und Modellvergleich für die Abnahme
```

- Der echte Lauf benötigt zusätzlich den lokalen Embedding-Dienst unter `EMBED_URL`.
- Der Standarddatensatz `entwicklung` dient zur Wahl von `RAG_SCHWELLE`. Der Datensatz `abnahme` verwendet festgelegte neue Fälle unter `data/testdaten/rag_abnahme.json`.
- Die Wachstumskontrolle prüft, ob ein frisch geschlossenes Ticket beim nächsten ähnlichen Fall gefunden wird.
- `--vergleich` speichert bei echtem Modellbetrieb auch Antworten derselben Fälle ohne Ticket-Historie. Der Mock bildet nur den Ablauf mit simulierten Ausgaben ab.
- Ergebnisse als Markdown und JSON stehen unter `data/laufzeit/auswertung/rag_*`.

## auswertung_doku.py

Mit laufendem Backend `python scripts/auswertung_doku.py` ausführen. Der Bericht
unter `data/laufzeit/auswertung/` enthält den Backend-Modus und das Ergebnis je
Testfall. Für den Vergleich mit dem echten Modell das Backend mit
`KI_MOCK=false` und dem lokalen llama-server starten.

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
