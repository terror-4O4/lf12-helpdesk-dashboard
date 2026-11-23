"""Ticketberatung über denselben Endpunkt wie im Dashboard; alle Daten bleiben im Test."""

import json
import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import app


class TicketfragenTest(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.tickets = app.lade_json(app.DATEN / "tickets.json")
        testdaten = Path(stack.enter_context(TemporaryDirectory()))
        stack.enter_context(patch.object(app, "wissensbasis", app.rag.Wissensbasis(testdaten / "wissen.json")))
        stack.enter_context(patch.object(app, "einbetter", app.rag.Einbetter("", mock=True)))
        stack.enter_context(patch.object(app, "lade_tickets", return_value=self.tickets))
        stack.enter_context(patch.object(app, "KI_MOCK", True))
        self.client = stack.enter_context(TestClient(app.app))

    def frage(self, nr, text, vorher=None):
        r = self.client.post(f"/api/tickets/{nr}/frage", json={"frage": text, "vorherige_frage": vorher})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_arbeitsanleitung_vergleichsfall_und_keine_livedaten(self):
        r = self.frage(1021, "Müssen wir etwas tun?")
        self.assertIn("Prüfe zeitnah die Belegung", r["antwort"])
        self.assertIn("archiviert", r["antwort"])
        self.assertNotIn("Arbeitsplätze", r["antwort"])
        self.assertIn("Im früheren Ticket #1020", r["antwort"])
        self.assertEqual(r["quellen"][1]["ticket_id"], 1020)
        self.assertIn("vorgehen", r["quellen"][0]["quelle"])
        self.assertTrue(r["quellen"][0]["links"][0]["url"].startswith("https://learn.microsoft.com/"))
        r = self.frage(1021, "Wie viel Speicher ist aktuell frei?")
        self.assertTrue(r["antwort"].startswith("Der Assistent hat keinen Zugriff auf aktuelle Messwerte"))

    def test_anleitung_bei_anderer_nummer_und_fremder_fall_geschuetzt(self):
        t = next(t for t in self.tickets if t["id"] == 1021)
        t["id"] = 9999
        fall = next(t for t in self.tickets if t["id"] == 1020)
        fall["kunde"] = "bau"
        r = self.frage(9999, "Was ist der nächste Schritt?")
        self.assertIn("Belegung", r["antwort"])
        self.assertNotIn("1020", r["antwort"])
        self.assertFalse(any(q.get("ticket_id") for q in r["quellen"]))
        self.assertIn("vorgehen", r["quellen"][0]["quelle"])
        self.assertIn("Wikipedia", r["quellen"][1]["quelle"])
        self.assertNotIn("damals", self.frage(9999, "Welcher frühere Fall passt?")["antwort"])

    def test_historie_anschlussfrage_und_andere_themen(self):
        r = self.frage(1021, "Gibt es einen ähnlichen gelösten Fall?")
        self.assertIn("Online-Archiv", r["antwort"])
        self.assertEqual([q["ticket_id"] for q in r["quellen"]], [1020])
        r = self.frage(1021, "Wie genau?", "Müssen wir etwas tun?")
        self.assertIn("Prüfe zeitnah die Belegung", r["antwort"])
        r = self.frage(1021, "Wie hoch ist die CPU-Temperatur?")
        self.assertNotIn("Postfach", r["antwort"])
        self.assertFalse(r["quellen"])

    def test_begriff_fakten_zugangsdaten_und_kundengrenze(self):
        r = self.frage(1021, "Was ist ein VPN?")
        self.assertEqual(r["modus"], "wikipedia")
        self.assertTrue(r["quellen"][0]["quelle"].startswith("Wikipedia"))
        r = self.frage(1021, "Welche IP hat das Gateway?")
        self.assertIn("192.168.50.1", r["antwort"])
        self.assertNotIn("Konnektor", r["antwort"])
        self.assertIn("Passwortmanager", self.frage(1021, "Passwort für den Server-Admin?")["antwort"])
        self.assertFalse(self.frage(1021, "Welches Gateway verwendet das Autohaus?")["quellen"])
        r = self.client.post("/api/tickets/1010/frage", json={"frage": "Was soll ich tun?"})
        self.assertEqual(r.status_code, 409)

    def test_fehlender_fall_und_bestaetigter_verweis(self):
        with patch.object(app, "erzeuge_vorschlag", return_value={
            "modus": "llama", "tokens": 8, "ergebnis": {"vorschlaege": []}
        }) as suche:
            r = self.frage(1023, "Was soll ich tun?")
            self.assertIn("keinen belegten Lösungsweg", r["antwort"])
            self.assertEqual(r["quellen"], [])
            self.assertTrue(suche.call_args.kwargs["nur_ticketkunde"])

    def test_action_auch_im_expliziten_dokumodus(self):
        t = next(t for t in self.tickets if t["id"] == 1021)
        r = self.client.post("/api/kunden/praxis/doku/suche", json={"frage": t["beschreibung"]}).json()
        self.assertIn("Prüfe zeitnah die Belegung", r["antwort"])
        self.assertNotIn("Arbeitsplätze", r["antwort"])

    def test_stoerung_verknuepft_aktenwissen_technik_und_vorfall(self):
        ticket = next(t for t in self.tickets if t["id"] == 1017)
        for frage in (ticket["beschreibung"], "Kanzleisoftware startet wieder nicht",
                      "Seit dem Reboot kommt keiner mehr in die Anwendung. Was prüfe ich zuerst?"):
            with self.subTest(frage=frage):
                r = self.frage(1017, frage)
                self.assertIn("STB-SRV01", r["antwort"])
                self.assertIn("protokoll", r["antwort"].lower())
                self.assertIn("Damaliger Lösungsweg", r["antwort"])
                self.assertIn("Ob dieselbe Ursache vorliegt", r["antwort"])
                self.assertEqual({q["ticket_id"] for q in r["quellen"] if "ticket_id" in q}, {1016})
                self.assertTrue(any(q["quelle"].startswith("doku/steuerbuero") for q in r["quellen"]))
                self.assertTrue(any(q.get("pruefschritte") for q in r["quellen"]))

    def test_neuer_befund_aendert_den_naechsten_schritt(self):
        r = self.frage(1017, "Der Dienst läuft bereits. Was prüfe ich jetzt?")
        self.assertIn("protokoll", r["antwort"].lower())
        self.assertNotIn("Status der", r["antwort"])
        self.assertNotIn("Damaliger Lösungsweg", r["antwort"])
        vpn = self.frage(1026, "Der VPN-Client zeigt jetzt verbunden. Nur die Freigabe ist nicht erreichbar.")
        self.assertIn("interne Ressource", vpn["antwort"])
        self.assertNotIn("Firmenprofil", vpn["antwort"])
        drucker = self.frage(1002, "Die Warteschlange ist jetzt leer, auf dem Papier kommt nichts an.")
        self.assertIn("Drucker selbst", drucker["antwort"])
        self.assertNotIn("Öffne die Warteschlange", drucker["antwort"])
        vpn = self.frage(1026, "Der Laptop baut keinen Tunnel auf. Im Client steht Verbindung fehlgeschlagen.")
        self.assertIn("Firmenprofil", vpn["antwort"])

    def test_konkrete_ki_formulierung_und_unbelegte_antworten(self):
        richtige_pruefung = "Kontrolliere auf STB-SRV01 den Status und den Starttyp der Dienstinstanz."
        for formulierung in [richtige_pruefung, "Starte den Datenbankserver neu.", "Prüfe den Status auf FAKE-SRV09."]:
            plan = json.dumps({"schritt": 0, "anweisung": formulierung, "rueckfrage": ""})
            with self.subTest(formulierung=formulierung), patch.object(app, "KI_MOCK", False), patch.object(
                    app, "frage_beratungsmodell", return_value=(plan, 40), create=True) as modell:
                r = self.frage(1017, "Was prüfe ich zuerst?")
                daten = json.loads(modell.call_args.args[0][1]["content"])
                self.assertIn("Starttyp", daten["frueherer_fall"]["damals"])
                self.assertTrue(any("STB-SRV01" in fakt for fakt in daten["kundenakte"]))
                self.assertTrue(daten["pruefungen"])
                self.assertEqual(r["tokens"], 40)
                if formulierung == richtige_pruefung:
                    self.assertIn(formulierung, r["antwort"])
                else:
                    self.assertNotIn(formulierung, r["antwort"])
                    self.assertIn("STB-SRV01", r["antwort"])

    def test_andere_kunden_und_offene_faelle_bleiben_ausgeschlossen(self):
        historisch = next(t for t in self.tickets if t["id"] == 1016)
        for kunde, status in [("bau", "geschlossen"), ("steuerbuero", "in_bearbeitung")]:
            historisch.update(kunde=kunde, status=status)
            r = self.frage(1017, "Kanzleisoftware zeigt wieder den Datenbankfehler.")
            self.assertNotIn("1016", json.dumps(r["quellen"]))
            self.assertNotIn("#1016", r["antwort"])

    def test_fehlende_fachnotiz_mit_konkreter_rueckfrage(self):
        text = "Tritt das Problem auch bei einer Testseite direkt am Gerät auf?"
        leer = {"modus": "llama", "tokens": None, "ergebnis": {"vorschlaege": []}}
        with patch.object(app, "KI_MOCK", False), patch.object(app, "erzeuge_vorschlag", return_value=leer):
            for frage in (text, "Welches Passwort steht im Passwortmanager?"):
                with self.subTest(frage=frage), patch.object(app, "frage_beratungsmodell", return_value=(
                        json.dumps({"rueckfrage": frage}), 25)):
                    r = self.frage(1027, "Die Etiketten bleiben leer, was ist der nächste Schritt?")
                    self.assertIn("Testseite", r["antwort"])
                    self.assertIn("Ursache ist offen", r["antwort"])
                    self.assertEqual(r["tokens"], 25)
                    self.assertNotIn("Passwort", r["antwort"])
                    if frage == text:
                        self.assertIn(text, r["antwort"])
