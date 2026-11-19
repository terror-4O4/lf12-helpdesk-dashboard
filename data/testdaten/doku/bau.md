# Bauunternehmen GmbH

## Umgebung
- 12 Arbeitsplätze (Windows 11 Pro), 3 Notebooks für die Bauleiter
- Microsoft 365 Business Standard, Outlook als Mailprogramm
- Branchensoftware: Bauzeiten-Programm mit Outlook-Add-In für Termine

## Server
- 1 Server (Windows Server 2022), Hostname `BAU-SRV01`, IP 192.168.10.5
- Rollen: Domänencontroller, Dateiserver, Druckserver

## Netzwerk und Firewall
- Netz 192.168.10.0/24, Gateway 192.168.10.1
- Firewall: Sophos XGS 87, VPN für die Bauleiter-Notebooks

## Drucker
- Multifunktionsgerät Büro, IP 192.168.10.40

## Software
- Bauzeiten-Programm: Add-In in Outlook. Nach Updates des Programms gab es bereits Startprobleme in Outlook (siehe Ticket #1001)

## Zugangsdaten
- Server-Admin: siehe Passwortmanager, Eintrag "bau / Server"
- Firewall-Admin: siehe Passwortmanager, Eintrag "bau / Firewall"

## Besonderheiten
- Bauleiter sind tagsüber meist auf Baustellen, Rückrufe am besten ab 16 Uhr
