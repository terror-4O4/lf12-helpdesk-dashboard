"""Testet die lokale Doku-Suche über ihre HTTP-Schnittstellen."""

import json
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import app
from scripts import auswertung_doku


class DokuApiTest(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.client = stack.enter_context(TestClient(app.app))

    def test_sollfaelle_im_mock_modus(self):
        daten = auswertung_doku.DATEN
        faelle = json.loads((daten / "fragen_doku.json").read_text(encoding="utf-8"))
        tickets = json.loads((daten / "tickets.json").read_text(encoding="utf-8"))
        with patch.object(app, "KI_MOCK", True), patch.object(app, "lade_tickets", return_value=tickets):
            for fall in faelle:
                with self.subTest(fall=fall["id"]):
                    if "ticket" in fall:
                        antwort = self.client.get(f"/api/tickets/{fall['ticket']}/doku")
                    else:
                        antwort = self.client.post(f"/api/kunden/{fall['kunde']}/doku/suche",
                                                   json={"frage": fall["frage"]})
                    self.assertEqual(antwort.status_code, 200, antwort.text)
                    self.assertEqual(auswertung_doku.pruefe_fall(fall, antwort.json()), [])

    def test_modell_waehlt_beleg_ohne_eigenen_antworttext(self):
        with patch.object(app, "KI_MOCK", False), patch.object(
            app, "frage_llama", return_value=('{"fundstelle": 1, "antwort": "frei erfunden"}', 5)
        ) as modell:
            antwort = self.client.post("/api/kunden/bau/doku/suche",
                                       json={"frage": "Welches Gateway hat das Netzwerk?"})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        r = antwort.json()
        self.assertEqual(r["modus"], "llama")
        self.assertEqual(r["tokens"], 5)
        self.assertEqual(r["quellen"][0]["quelle"], "doku/bau.md#netzwerk-und-firewall")
        self.assertEqual(r["antwort"], r["quellen"][0]["text"])
        self.assertNotIn("frei erfunden", r["antwort"])
        modell.assert_called_once()

    def test_unpassenden_beleg_durch_modell_ablehnen(self):
        with patch.object(app, "KI_MOCK", False), patch.object(
            app, "frage_llama", return_value=('{"fundstelle": 0}', 4)
        ) as modell:
            antwort = self.client.post("/api/kunden/bau/doku/suche",
                                       json={"frage": "Welches Gateway nutzt das Testnetz mit Glasfaser?"})
        self.assertEqual(antwort.status_code, 200, antwort.text)
        self.assertEqual(antwort.json()["quellen"], [])
        self.assertEqual(antwort.json()["antwort"], auswertung_doku.KEINE_FUNDSTELLE)
        modell.assert_called_once()

    def test_zugangsdaten_leerfrage_und_fremdkunde_ohne_modell_aufruf(self):
        with patch.object(app, "KI_MOCK", False), patch.object(app, "frage_llama") as modell:
            zugang = self.client.post("/api/kunden/bau/doku/suche",
                                      json={"frage": "Wie lautet das Passwort für den Server-Admin?"})
            leer = self.client.post("/api/kunden/bau/doku/suche", json={"frage": "   "})
            fremd = self.client.post("/api/kunden/unbekannt/doku/suche",
                                    json={"frage": "Welches Gateway hat das Netzwerk?"})
        self.assertEqual(zugang.status_code, 200, zugang.text)
        self.assertIn("Passwortmanager", zugang.json()["antwort"])
        self.assertEqual(leer.status_code, 422, leer.text)
        self.assertEqual(fremd.status_code, 404, fremd.text)
        modell.assert_not_called()
