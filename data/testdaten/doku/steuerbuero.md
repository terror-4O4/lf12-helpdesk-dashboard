# Steuerberatung PartG mbB

## Umgebung
- 6 Arbeitsplätze (Windows 11 Pro), 1 Notebook für die Partnerin
- Microsoft 365 Business Standard, Outlook als Mailprogramm

## Server
- 1 Server (Windows Server 2022), Hostname `STB-SRV01`, IP 192.168.30.5
- Rollen: Domänencontroller, Dateiserver
- SQL-Server für die Kanzleisoftware (Dienst muss nach Updates laufen, siehe Ticket #1016)

## Netzwerk und Firewall
- Netz 192.168.30.0/24, Gateway 192.168.30.1
- Firewall: Sophos XGS 87
- Erster Stock: Netzwerkdosen vorhanden, aber noch nicht gepatcht

## Drucker
- Multifunktionsgerät Empfang, IP 192.168.30.40

## Software
- Kanzleisoftware (Client auf allen Arbeitsplätzen, Datenbank auf `STB-SRV01`)

## Zugangsdaten
- Server-Admin: siehe Passwortmanager, Eintrag "steuerbuero / Server"
- Firewall-Admin: siehe Passwortmanager, Eintrag "steuerbuero / Firewall"

## Besonderheiten
- Die Kanzleisoftware ist das zentrale Programm. Fällt sie für mehrere Arbeitsplätze aus, steht die Kanzlei, daher immer sehr hohe Priorität
