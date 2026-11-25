# Kundendokumentation und Fallsuche prüfen

Im Repo-Hauptordner bei laufendem Backend prüft `python scripts/auswertung_doku.py`, ob die Antworten die erwartete Fundstelle der jeweiligen Kundenakte nennen. Ziel sind mindestens 80 % der vorbereiteten Fragen. Der Bericht enthält auch Fälle ohne passende Fundstelle.

In der Demo zu Ticket #1004 lässt sich nach dem Netzwerk-Gateway fragen. Bei der Frage nach dem Server-Admin-Passwort soll die Akte auf den Passwortmanager verweisen.

Für die Fallsuche verwendet `python scripts/auswertung_rag.py --datensatz abnahme --vergleich` die vorbereiteten positiven und negativen Fälle. Die Referenzen und die Ergebnisse für Fälle ohne Treffer werden getrennt ausgewiesen.
