# Backend

Python-Backend des Dashboards.

**Aufgaben**
- Tickets und Kundendoku aus `data/testdaten/` laden
- Prompts bauen und an den llama-server schicken (Adresse und Key aus `.env`)
- Ergebnisse (Priorität, Spam ja/nein, Lösungsvorschläge) ans Frontend liefern

**Hinweis:** Mit `KI_MOCK=true` in der `.env` liefert das Backend Beispielantworten. So kann ohne laufenden KI-Server entwickelt werden.

Abhängigkeiten kommen in `requirements.txt`.
