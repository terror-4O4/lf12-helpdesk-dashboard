# Allgemeinarztpraxis GbR

## Umgebung
- 8 Arbeitsplätze (Windows 11 Pro): Anmeldung (2), Behandlungsräume (4), Labor, Büro
- Microsoft 365 Business Premium mit mehrstufiger Authentifizierung (Authenticator-App)
- Gemeinsames Postfach "Praxis" für Laborbefunde und Patientenanfragen

## Server
- 1 Server (Windows Server 2022), Hostname `PX-SRV01`, IP 192.168.50.5
- Rollen: Domänencontroller, Datenbank der Praxissoftware

## Netzwerk und Firewall
- Netz 192.168.50.0/24, Gateway 192.168.50.1
- Firewall: Sophos XGS 107
- Anbindung an das Gesundheitsnetz über einen eigenen Konnektor

## Drucker
- Laserdrucker Anmeldung, IP 192.168.50.40
- Etikettendrucker Labor, per USB am Labor-PC

## Software
- Praxissoftware (Client auf allen Arbeitsplätzen, Datenbank auf `PX-SRV01`)
- Kartenlesegerät an Anmeldeplatz 1

## Zugangsdaten
- Server-Admin: siehe Passwortmanager, Eintrag "praxis / Server"
- Microsoft-365-Admin: siehe Passwortmanager, Eintrag "praxis / M365"

## Besonderheiten
- Fallen die Patientenaufnahme (Kartenlesegerät) oder der Empfang der Laborbefunde per E-Mail aus, immer sehr hohe Priorität
- Fernwartung nur nach Freigabe durch die Praxisleitung (Patientendaten)

## Vorgehen bei Postfach fast voll

Prüfe zeitnah die Belegung des betroffenen Praxispostfachs. Im Microsoft-365-Admincenter zeigt der Bericht zur Postfachnutzung den verbrauchten Speicher und das eingestellte Limit. Vergleiche beide Werte und beachte den Stand des Berichts.

Ist der Speicher tatsächlich knapp, stimme mit der Praxisleitung ab, welche Nachrichten gemäß den geltenden Aufbewahrungsregeln archiviert werden dürfen. Falls externe Laborbefunde bereits ausbleiben, melde den Ausfall sofort an den Support.

Vergleichsfall: #1020

[Microsoft Learn – Bericht zur Postfachnutzung](https://learn.microsoft.com/de-de/microsoft-365/admin/activity-reports/mailbox-usage?view=o365-worldwide)
