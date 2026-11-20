# Frontend

Dashboard-Oberfläche in reinem HTML, CSS und JavaScript. **Kein Framework, keine CDNs, keine externen Schriften.** So läuft alles ohne Internet, und es gibt nichts zu installieren oder zu bauen.

## Starten

Das Backend liefert das Dashboard gleich mit aus. Backend starten (siehe [`backend/README.md`](../backend/README.md)), dann im Browser:

- **http://127.0.0.1:8000/**: Dashboard
- **http://127.0.0.1:8000/?jetzt=2026-11-19T11:30**: Dashboard mit fester Demo-Uhrzeit (siehe unten)

Zum Entwickeln reicht `KI_MOCK=true` in der `.env`, dann ist kein KI-Server nötig. Änderungen an HTML, CSS oder JS sind nach einem Neuladen im Browser sichtbar.

## Ansichten

| Ansicht | Adresse | Inhalt |
|---|---|---|
| Übersicht | `#/uebersicht` | Kennzahlen, Handlungsbedarf (Neu und Antwort erhalten, dringendste zuerst), eigene Tickets, persönliche To-dos |
| Tickets | `#/tickets` | Alle Tickets mit Suche und Filtern. Filter stehen in der Adresse, z. B. `#/tickets?status=neu&kunde=bau` |
| Ticket | `#/ticket/1002` | Links Nachricht, Bearbeiten (mit Ursache und Lösungsweg) und Verlauf, rechts KI-Einschätzung, ähnliche gelöste Fälle und Kundendoku |
| Spam-Prüfung | `#/spam` | Spam-Verdacht der KI bestätigen oder verwerfen |
| Neues Ticket | Knopf oben rechts | Mail einfügen, Ticket anlegen, KI bewertet direkt |
| KI-Assistent | Knopf links unten | Freie Fragen an die KI, optional mit einem Ticket als Kontext |

## Gestaltung

- Neutral, Farbe nur für Status, Priorität, SLA-Ampel und KI-Inhalte
- **Alles, was von der KI kommt, ist violett und mit ✦ gekennzeichnet.** Eine Priorität mit ✦ hat die KI gesetzt, ohne ✦ ein Mitarbeiter.
- Hell- und Dunkelmodus folgen der Systemeinstellung

## SLA-Ampel

Einstellungen in [`js/config.js`](js/config.js).

| Priorität | Reaktionszeit |
|---|---|
| Sehr hoch | 30 Min. |
| Hoch | 2 Std. |
| Mittel | 8 Std. |
| Niedrig | 24 Std. |
| noch nicht bewertet | 2 Std. |

- Die SLA läuft bei **Neu** und **Antwort erhalten**, gemessen ab dem letzten Statuswechsel
- Grün = weniger als die Hälfte der Zeit verbraucht, gelb = mehr als die Hälfte, rot = überschritten
- Bei In Bearbeitung, Warten auf Kunde und Geparkt ist sie pausiert (leerer Kreis)
- **Übernehmen** im Ticket weist es dir zu und setzt neue Tickets auf In Bearbeitung, damit stoppt die SLA

**Demo-Uhrzeit:** Die Testdaten haben feste Zeitstempel. Mit echter Uhrzeit wäre bei der Präsentation alles rot. Deshalb lässt sich „jetzt“ festlegen, entweder per Adresse (`?jetzt=2026-11-19T11:30`) oder in `config.js` (`DEMO_JETZT`). Oben rechts steht dann ein gelber Hinweis „Demo-Zeit“.

## Datenschutz und Sicherheit

- Eine **Content-Security-Policy** in `index.html` erlaubt nur Dateien und Anfragen an den eigenen Server. Selbst wenn jemand eine externe Adresse einbaut, blockiert der Browser sie.
- Inhalte aus Tickets werden immer als Text eingefügt, nie als HTML. Eine Mail mit `<script>` richtet im Dashboard nichts an. Deshalb kein `innerHTML` verwenden, sondern die Hilfsfunktion `h()` aus `js/hilfen.js`.
- Zugangsdaten zeigt das Dashboard nie an, die Kundendoku enthält nur Verweise auf den Passwortmanager.
- Im Browser gespeichert werden nur der gewählte Mitarbeiter und die persönlichen To-dos (`localStorage`), sonst nichts.

## Dateien

| Datei | Inhalt |
|---|---|
| `index.html` | Grundgerüst: Seitenleiste, Kopfzeile, Inhaltsbereich |
| `css/style.css` | Gestaltung, Farben, Hell/Dunkel |
| `js/config.js` | Einstellungen (SLA, Texte, Demo-Uhrzeit) |
| `js/api.js` | Alle Aufrufe ans Backend |
| `js/hilfen.js` | Elemente bauen, Zeiten, SLA-Berechnung, Badges, Markdown |
| `js/zustand.js` | Geladene Daten, Mitarbeiter, Meldungen |
| `js/app.js` | Navigation und Kopfzeile |
| `js/ansichten/*.js` | Eine Datei pro Ansicht |

## Noch offen

- Fragen zur Kundendoku im KI-Assistenten (Backend schickt die Doku als Kontext mit)
- Passend/Unpassend-Bewertung der KI-Vorschläge speichern (Messziel 80 %)
- Mitarbeiter und To-dos aus dem Backend statt aus dem Browser
