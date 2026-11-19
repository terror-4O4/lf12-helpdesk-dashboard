# Logistik-Firma AG

## Umgebung
- 25 Arbeitsplätze (Windows 11 Pro), davon 6 im Lager
- 2 Terminalserver für die Lagerarbeitsplätze

## Server
- Hyper-V-Host `LOG-HV01` mit 3 VMs:
  - `LOG-DC01` (Domänencontroller), IP 10.20.0.10
  - `LOG-TS01` und `LOG-TS02` (Terminalserver), IP 10.20.0.21 und 10.20.0.22
- Druckserver-Rolle auf `LOG-DC01`

## Netzwerk und Firewall
- Netz 10.20.0.0/24, Gateway 10.20.0.1
- Firewall: Fortinet FortiGate 40F
- Lager per WLAN angebunden (2 Access Points), Lagerdrucker per Kabel

## Drucker
- Lagerdrucker (Lieferscheine), IP 10.20.0.51, läuft über den Druckserver
- Etikettendrucker Versand, IP 10.20.0.52

## Software
- Warenwirtschaft läuft auf den Terminalservern

## Zugangsdaten
- Domänen-Admin: siehe Passwortmanager, Eintrag "logistik / Domäne"
- Firewall-Admin: siehe Passwortmanager, Eintrag "logistik / Firewall"

## Besonderheiten
- Ausfall des Lagerdruckers stoppt den Warenausgang, daher immer hohe Priorität
