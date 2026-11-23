# Projektdokumentation LF12 Helpdesk

Das Projekt untersucht, wie ein lokal betriebenes Sprachmodell die Arbeit im IT-Support unterstützen kann. Die Fassung V2.1 umfasst Ticketübersicht, Priorisierung, Lösungsvorschläge aus gelösten Fällen und die Suche in der Kundendokumentation. Die Abgabe ist für den **11. Dezember 2026** vorgesehen. Die Präsentation folgt spätestens am **16. Dezember 2026**.

## Umsetzung

- **Ticketübersicht.** Das Dashboard zeigt Status, Ticketalter und Wartezeit. Neue Tickets und Kundenantworten werden als Handlungsbedarf hervorgehoben. Die Anzeige leitet die Wartezeit und die prioritätsabhängige SLA aus der Statushistorie ab.
- **Spam-Prüfung.** Der Eingangsfilter prüft Betreff und Nachricht. Verdachtsfälle wie eine unerwünschte Verkaufsaufforderung erscheinen mit Prüfgrund in der Warteschlange. Der Support kann sie bestätigen oder freigeben.
- **Priorisierung.** Bei regulären Anfragen bestimmen Ticketregeln und lokales Sprachmodell Kategorie und Priorität. Das Dashboard zeigt die Herkunft je Feld und den Beleg aus der Nachricht. Der Support kann die Priorität ändern.
- **Ähnliche Fälle.** Gelöste Tickets mit dokumentiertem Lösungsweg bilden eine Wissensbasis. Die semantische Suche priorisiert ähnliche Fälle, bevorzugt beim selben Kunden. Das Sprachmodell wählt daraus bis zu drei passende Tickets. Das Dashboard zeigt deren dokumentierte Ursachen und Lösungswege mit verlinkten Ticketnummern. Bei leerer Auswahl meldet die Anwendung, dass kein passender Fall vorliegt.
- **Kundendokumentation.** Das Dashboard sucht zum Ticket und im Assistenten in der jeweiligen Kundenakte. Die API liefert Textauszüge, Fundstellen und hinterlegte Portal-Links. Bei einer Anfrage nach Zugangsdaten zeigt die Anwendung die hinterlegten Passwortmanager-Verweise.
- **Ticketberatung.** Der Assistent öffnet auf dem aktuellen Supportticket. Bei einer Handlungsfrage sucht er nach einer passenden Arbeitsanweisung in der Kundenakte oder einem belegten Lösungsweg in der Historie desselben Kunden. Für IT-Begriffe stehen sieben lokal gespeicherte Fachnotizen mit Links auf die verwendeten Wikipedia-Artikelfassungen bereit.

## Betrieb und Daten

Im Browser läuft die selbst programmierte Oberfläche mit HTML, CSS und JavaScript. FastAPI liefert Daten und statische Dateien aus. Zwei lokal betriebene llama.cpp-Dienste übernehmen Chat und Embeddings. Das Datenverzeichnis simuliert ein Ticketsystem mit einer JSON-Liste und fiktiven Kundendokumenten im Unterordner `doku/`. Die Anwendung bearbeitet eine Arbeitskopie. Ein einzelner Uvicorn-Worker synchronisiert das Lesen und Schreiben der Ticketdaten. Die Modellberechnung erfolgt zwischen diesen Zugriffen.

Die Entwicklungsdaten sind vollständig fiktiv. Dokumente führen Zugangsdaten nur als Passwortmanager-Verweise. Lokale Konfiguration und API-Schlüssel bleiben in der ignorierten `.env`. Zugriff von Gruppenrechnern ist im vorgesehenen Betrieb auf den abgestimmten Tailscale-Zugang begrenzt. Für Bereitstellung und Review gelten die [Regeln zur Mitarbeit](../CONTRIBUTING.md).

## Projektablauf

Auf den Aufbau der lokalen Dienste und der Ausgangsdaten folgten Ticketübersicht, KI-Priorisierung und die Suche über gelöste Fälle. Die Erweiterung verbindet die Kundendokumentation mit dem Dashboard, schützt parallele Ticketänderungen und ergänzt prüfbare Vergleiche. Der nächste Meilenstein ist der protokollierte Modelllauf auf dem Mac Pro. Erst dessen Ergebnisse erlauben eine Aussage darüber, ob die Messziele für die vorgesehene Konfiguration erreicht werden.

## Nachweise

- [Prüf- und Demoablauf](test-und-demo.md)
- [Datenschutz und Projektrisiken](datenschutz-und-risiken.md)
- [Datenformat und Testdaten](datenformat.md)
- [Start und lokale Dienste](../backend/README.md)
- [Auswertungsskripte](../scripts/README.md)
