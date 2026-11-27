# Backend
Das aktuelle Backend, fortan genannt Haupt-Anwendung soll refactored werden um einen höheren Standard an Modularität und Lesbarkeit zu erreichen:
- Die Haupt-Anwendung soll die Hexagonale Architektur verwenden siehe [Wikipedia Artikel](https://de.wikipedia.org/wiki/Hexagonale_Architektur)
- Um code weiter zu decouplen soll ein Event-System verwendet werden
- Dabei sollen vor allem die Anbindungen an das Ticket-System und die Dokumentationsquellen modular gestaltet werden, um später eine vielzahl von Ticket Systemen und internen Dokumentationsdatenquellen wie Wikis oder Netzlaufwerke mit dokumentationsdateien unterstützen zu können (**Hohe Wichtigkeit**)
- Die interaktionen mit dem Test-Frontend werden über eine Implementation der Interfaces für Ticket Systeme und Dokumentationsquellen bereitgestellt, diese Implementation kommuniziert mit dem Test-Frontend über eine JSON-Rest API

# Test-Frontend
Das Test-Frontend simuliert ein Ticketsystem für die Testumgebung und soll zukünftig aus drei Teilen bestehen, welche vom Test-Frontend Server aus live-updated werden können mithilfe von Server-Sent-Events.
- Um die Live Updates zu bewerkstelligen wird die [Datastar Bibliothek](https://data-star.dev/) eingebunden sowie ihre Python API ``` pip install datastar-py```
- Der Test-Frontend Server für das Test-Frontend ist separat von der Haupt-Anwendung und enthält die bereits genannte Datastar Python API sowie eine Template Engine (Bibliothek nach wahl, nicht selbst implementieren). Sowie die nötigen Abhängigkeiten um eine JSON-Rest Schnittstelle für die Anbindung der Haupt-Anwendung
- Die drei Teile aus denen das Test-Frontend bestehen soll sind
  - Das Dashboard, um das Ticketsystem von der Seite eines internen Mitarbeiters Simuliert (wird von dem aktuellen Frontend übernommen). **WICHTIG:** Das Dashboard sollte über Server-Sent-Events sofort neu erstellte Tickets anzeigen ohne dass der Workflow unterbrochen wird und ohne einen ganzseitigen Refresh verwenden zu müssen
  - Ein Portal, mit dem interaktionen mit dem Ticketsystem von externen Dienstleistern simuliert werden kann, dies ist momentan nur eine seite zum erstellen neuer Tickets.
  - Eine LLM übliche Chatseite, damit interne mitarbeiter direkt Fragen über Tickets und interne Dokumentation stellen können, diese Seite ist vom Workflow angepasst und besitzt Seitenleisten ansicht für Tickets und Interne Dokumentation die für den Prompt relevant sind
- Clientseitige Darstellungslogik sollte zukünftig vermieden werden wenn möglich und dazu sollen die Features der Datastar Bibliothek ausgenutzt werden
- Das Test Backend benötigt anders als die Haupt-Anwendung nicht unbedingt eine Hexagonale Architektur, aber falls manuelle Anpassungen gemacht werden müssen sollte der Code Trotzdem Lesbar sein und ein Event-System zum decouplen von Code verwenden. Wenn für lesbarkeit und manuelle Anpassbarkeit nötig, dann für das Test-Frontend die Model-View-Controller Architektur verwenden
