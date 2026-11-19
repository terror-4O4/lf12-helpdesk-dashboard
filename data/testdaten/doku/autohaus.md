# Autohaus GmbH & Co. KG

## Umgebung
- 14 Arbeitsplätze (Windows 11 Pro): Verkauf, Service, Werkstatt, Buchhaltung
- 3 Notebooks für die Serviceberatung
- Microsoft 365 Business Basic

## Server
- 1 Server (Windows Server 2022), Hostname `AH-SRV01`, IP 172.16.5.5
- Rollen: Domänencontroller, Dateiserver (Freigabe `Scans` für das Multifunktionsgerät)

## Netzwerk und Firewall
- Netz 172.16.5.0/24, Gateway 172.16.5.1
- Firewall: Fortinet FortiGate 40F
- Werkstatt per Kabel, Ausstellungsraum per WLAN

## Drucker
- Multifunktionsgerät Büro, IP 172.16.5.40, Scannen in Ordner über den Benutzer `scan` auf die Freigabe `Scans`
- Laserdrucker Werkstatt, IP 172.16.5.41

## Software
- Dealer-Management-System (DMS) als Webanwendung des Herstellers
- Werkstattplaner auf dem PC an der Fahrzeugannahme

## Zugangsdaten
- Server-Admin: siehe Passwortmanager, Eintrag "autohaus / Server"
- Scan-Benutzer: siehe Passwortmanager, Eintrag "autohaus / Scan"

## Besonderheiten
- Fällt der PC an der Fahrzeugannahme aus, können keine Fahrzeuge angenommen werden, daher immer sehr hohe Priorität
- Samstags bis 13 Uhr geöffnet
