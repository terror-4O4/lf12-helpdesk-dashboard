"""Ticketberatung über denselben Endpunkt wie im Dashboard; alle Daten bleiben im Test."""

import unittest
from contextlib import ExitStack
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import app


class TicketfragenTest(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.tickets = app.lade_json(app.DATEN / "tickets.json")
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
        self.assertEqual(len(r["quellen"]), 1)
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
