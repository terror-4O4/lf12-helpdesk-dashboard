# Mitarbeiten am Projekt

## Ablauf

```
Trello-Karte  ──►  Branch  ──►  Commits  ──►  Pull Request  ──►  Review (Marlon)  ──►  Merge in main
```

### 1. Aktuellen Stand holen

Vor jeder neuen Aufgabe:

```bash
git switch main
git pull
```

### 2. Branch anlegen

Ein Branch pro Trello-Karte. Namensschema:

| Präfix | Wofür | Beispiel |
|---|---|---|
| `feature/` | neue Funktion | `feature/ki-textfeld` |
| `fix/` | Fehlerbehebung | `fix/sla-ampel-farbe` |
| `docs/` | Dokumentation | `docs/datenschutz-kapitel` |
| `test/` | Tests, Testdaten | `test/spam-testtickets` |

```bash
git switch -c feature/ki-textfeld
```

### 3. Committen

Kleine, sinnvolle Schritte. Commit-Nachricht kurz und auf Deutsch, im Imperativ:

```
Füge KI-Textfeld zum Dashboard hinzu
Behebe falsche Farbe bei verletzter SLA
```

```bash
git add .
git commit -m "Füge KI-Textfeld zum Dashboard hinzu"
git push -u origin feature/ki-textfeld
```

### 4. Pull Request öffnen

Auf GitHub erscheint nach dem Push ein Button **„Compare & pull request“**. Ziel ist immer `main`. Die Checkliste in der Vorlage ausfüllen und die Trello-Karte nach **„Review“** schieben.

### 5. Review

Marlon prüft den Code. Bei Anmerkungen: im selben Branch weiterarbeiten und erneut pushen, der PR aktualisiert sich automatisch. Nach dem Merge wird der Branch gelöscht und die Trello-Karte kommt nach **„Abgeschlossen“**.

## Regeln

- **Nie direkt auf `main` pushen.** Das ist technisch gesperrt.
- **Keine Secrets** (Passwörter, API-Keys, Tokens) und **keine echten Daten** committen.
- **Keine großen Dateien** (Modelle, Videos). Bilder für die Doku nur komprimiert.
- Bei Konflikten oder Problemen mit Git: lieber kurz in der Gruppe fragen als mit `--force` arbeiten.

## Hilfreiche Befehle

| Befehl | Was er macht |
|---|---|
| `git status` | Zeigt, welche Dateien geändert sind |
| `git log --oneline -10` | Die letzten 10 Commits kompakt |
| `git diff` | Zeigt noch nicht gestagete Änderungen |
| `git restore <datei>` | Verwirft lokale Änderungen an einer Datei |
| `git switch main && git pull` | Zurück auf main und aktuellen Stand holen |
