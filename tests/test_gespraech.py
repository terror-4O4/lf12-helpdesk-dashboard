"""Ein Themenwechsel darf keine weitere Diagnose oder Kundendaten auslösen."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import app


class Gespraechstest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)
        self.addCleanup(self.client.close)
        self.tickets = app.lade_json(app.DATEN / "tickets.json")
        bestand = patch.object(app, "lade_tickets", return_value=self.tickets)
        bestand.start()
        self.addCleanup(bestand.stop)

    def test_themenwechsel_trotz_ticket_und_verlauf(self):
        for url in ["/api/tickets/1025/frage", "/api/ki/frage"]:
            for frage in ["Wie ist das wetter heute", "Regnet es morgen in Berlin?",
                          "Wie steht es in der Bundesliga?"]:
                with self.subTest(url=url, frage=frage), patch.object(
                        app, "frage_beratungsmodell", side_effect=AssertionError("Modell aufgerufen")), patch.object(
                        app, "berate_zum_ticket", side_effect=AssertionError("Ticketsuche aufgerufen")):
                    body = {"frage": frage}
                    if "tickets/" in url:
                        body["verlauf"] = ["Was ist der nächste Schritt?", "Das Konto ist gesperrt."]
                    antwort = self.client.post(url, json=body)
                    self.assertEqual(antwort.status_code, 200)
                    daten = antwort.json()
                    self.assertEqual(daten["modus"], "themenfremd")
                    self.assertEqual(daten["quellen"], [])
                    self.assertNotIn("Konto", daten["antwort"])

    def test_wetter_im_technischen_kontext_und_echte_kurzantwort(self):
        with patch.object(app, "KI_MOCK", True), patch.object(app, "berate_zum_ticket",
                return_value=("Technische Hilfe", [], "ticket", None)) as beratung:
            for frage in ["Das Konto ist weiterhin gesperrt.", "Wie genau?", "Es geht noch nicht."]:
                with self.subTest(frage=frage):
                    daten = self.client.post("/api/tickets/1025/frage", json={
                        "frage": frage, "verlauf": ["Was ist der nächste Schritt?", "Wie ist das Wetter heute?"]
                    }).json()
                    self.assertEqual(daten["modus"], "ticket")
                    self.assertEqual(beratung.call_args.args[-1], ["Was ist der nächste Schritt?"])
        with patch.object(app, "KI_MOCK", True):
            daten = self.client.post("/api/ki/frage", json={"frage": "Mein WLAN fällt bei Regen aus."}).json()
            self.assertNotIn(daten["modus"], {"themenfremd", "unklarer_bezug"})
        for frage in ["Meine Wetter-App startet nicht.", "Wie behebe ich einen Druckerstau?"]:
            with self.subTest(frage=frage), patch.object(app, "KI_MOCK", True), patch.object(
                    app, "berate_zum_ticket", side_effect=AssertionError("Falsches Ticket")):
                daten = self.client.post("/api/tickets/1025/frage", json={"frage": frage}).json()
                self.assertNotIn(daten["modus"], {"ticket", "themenfremd", "unklarer_bezug"})
                self.assertNotIn("Konto", daten["antwort"])

    def test_neues_thema_ohne_schluesselwort(self):
        for auswahl, modus in [("fachfremd", "themenfremd"), ("unklar", "unklarer_bezug"),
                               ("unlesbar", "unklarer_bezug")]:
            with self.subTest(auswahl=auswahl), patch.object(app, "KI_MOCK", False), patch.object(
                    app, "frage_beratungsmodell", return_value=(auswahl, 3)) as modell, patch.object(
                    app, "berate_zum_ticket", side_effect=AssertionError("Ticketberatung aufgerufen")):
                daten = self.client.post("/api/tickets/1025/frage", json={
                    "frage": "Wer malte die Mona Lisa?", "verlauf": ["Was ist der nächste Schritt?"]
                }).json()
                modell.assert_called_once()
                self.assertEqual(daten["modus"], modus)
                self.assertEqual(daten["quellen"], [])

    def test_unbekannte_fachfrage_an_allgemeine_hilfe(self):
        with patch.object(app, "KI_MOCK", False), patch.object(
                app, "frage_beratungsmodell", side_effect=[("it", 1), ("Eine IT-Antwort.", 4)]) as modell:
            daten = self.client.post("/api/tickets/1025/frage", json={
                "frage": "Wie konfiguriere ich ein Nix-Flake?"
            }).json()
            self.assertEqual(daten["modus"], "llama")
            self.assertEqual(daten["quellen"], [])
            self.assertNotIn("Verkäufer", str(modell.call_args))

    def test_anschlussfrage_verwendet_passenden_vorgaenger(self):
        with patch.object(app, "KI_MOCK", False), patch.object(
                app, "frage_beratungsmodell", return_value=("fachfremd", 3)), patch.object(
                app, "berate_zum_ticket", return_value=("Technische Hilfe", [], "ticket", None)) as beratung:
            self.client.post("/api/tickets/1025/frage", json={
                "frage": "Wie genau?", "verlauf": ["Das Konto ist gesperrt.", "Wer malte die Mona Lisa?"]})
            self.assertEqual(beratung.call_args.args[-1], ["Das Konto ist gesperrt."])
        with patch.object(app, "allgemeine_it_antwort", return_value={"modus": "llama"}) as allgemein:
            daten = self.client.post("/api/tickets/1025/frage", json={
                "frage": "Wie genau?", "verlauf": ["Meine Wetter-App startet nicht."]}).json()
            self.assertEqual(daten["modus"], "llama")
            self.assertIn("Wetter-App", allgemein.call_args.args[0])
