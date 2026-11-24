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
| Übersicht | `#/uebersicht` | Kennzahlen, Handlungsbedarf (Neu und Antwort erhalten, dringendste zuerst), eigene Tickets, persönliche To-dos. Die Übersicht aktualisiert sich alle 30 Sekunden, wenn keine Eingabe aktiv ist. |
| Tickets | `#/tickets` | Alle Tickets mit Ticketalter, Wartezeit, Suche und Filtern. Filter stehen in der Adresse, z. B. `#/tickets?status=neu&kunde=bau` |
| Ticket | `#/ticket/1002` | Nachricht, Bearbeitung, Verlauf, KI-Einschätzung, ähnliche Fälle und automatisch gefundene Abschnitte der Kundendoku |
| Spam / Werbung | `#/spam` | Zeigt aktuelle Verdachtsfälle und ihren Prüfgrund. Manuell freigegebene Nachrichten stehen separat unter „Vom Support freigegeben“. Im offenen Ticket setzt „Eingang erneut prüfen“ die Freigabe zurück und wendet den Filter erneut an. |
| Neues Ticket | Knopf oben rechts | Nachricht eingeben und automatisch auf Spam prüfen. Freie Supporttickets lassen sich beim Anlegen auf Wunsch von der KI bewerten. |
| KI-Assistent | Seitenleiste oder „KI zu diesem Ticket fragen“ | Nutzt am offenen Supportticket die Nachricht, passende Kundeninformationen, frühere Lösungen und lokales IT-Wissen. Außerhalb des Tickets beantwortet er allgemeine IT-Fragen. Quellen lassen sich unter der Antwort aufklappen. |

Der Spam-Zähler und die Warteschlange berücksichtigen offene Verdachtsfälle bereits vor einer KI-Bewertung. Ein offenes Supportticket lässt sich in der Ticketansicht unter **Nachrichtenaktionen** auch manuell als Spam markieren und schließen. Ein als Spam bestätigtes Ticket kann der Support dort als neues Supportticket wieder öffnen. In der Ticketliste zeigt **Alle inkl. geschlossen** auch die ausgesonderten Nachrichten.

## Gestaltung

- Neutral, Farbe nur für Status, Priorität, SLA-Ampel und KI-Inhalte
- In der Liste kennzeichnet „· KI“ eine vom lokalen Sprachmodell vorgeschlagene Priorität. Im Ticket steht die Herkunft im Klartext neben Priorität und Kategorie. Von Hand gesetzte Prioritäten haben Vorrang.
- Hell- und Dunkelmodus folgen der Systemeinstellung

## SLA-Ampel

Einstellungen in [`js/config.js`](js/config.js).

| Priorität | Reaktionszeit |
|---|---|
| Sehr dringend | 30 Min. |
| Hoch | 2 Std. |
| Normal | 8 Std. |
| Niedrig | 24 Std. |
| noch nicht bewertet | 2 Std. |

- Ticketalter wird ab Erstellung angezeigt. Die Wartezeit zeigt, wie lange im aktuellen Status schon eine Reaktion des Kunden oder des Supports aussteht.
- Die SLA läuft bei **Neu** und **Antwort erhalten**, gemessen ab dem letzten Statuswechsel
- Grün = weniger als die Hälfte der Zeit verbraucht, gelb = ab der Hälfte, rot = Frist erreicht oder überschritten
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

## Tests

Aus dem Repo-Hauptordner mit Node.js 24 ausführen: `node --test tests/test_dashboard.mjs`.

## Noch offen

- Passend/Unpassend-Bewertung der KI-Vorschläge speichern (Messziel 80 %)
- Mitarbeiter und To-dos aus dem Backend statt aus dem Browser
