"""Die Dashboard-Bewertung und die reguläre Messung benutzen dieselbe Modellantwort."""

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import app, eingang
from scripts import auswertung


class ModellbewertungTest(unittest.TestCase):
    def setUp(self):
        pfad = Path(self.enterContext(TemporaryDirectory())) / "tickets.json"
        self.enterContext(patch.object(app, "LAUFZEIT_TICKETS", pfad))
        self.enterContext(patch.object(app, "KI_MOCK", False))
        self.client = self.enterContext(TestClient(app.app))
        self.werbung = self.client.post("/api/tickets", json={
            "kunde": "bau", "titel": "Nur heute", "beschreibung": "50 % Rabatt, jetzt bestellen!",
        }).json()
        self.roh = {"kategorie": "Software", "prioritaet": "hoch", "spam": False,
                    "begruendung": "Unveränderte Begründung des Modells."}

    def test_dashboard_und_messung_nutzen_projektprompt_kontext_und_rohwerte(self):
        self.assertTrue(self.werbung["regelhinweise"])
        prompt = auswertung.PROMPTS["angepasst"]
        self.assertEqual(hashlib.sha256(prompt.encode()).hexdigest()[:12], "bed41d8163d7")
        mit_id = f"/api/tickets/{self.werbung['id']}"
        with patch.object(app, "frage_llama", return_value=(json.dumps(self.roh), 12)) as modell:
            antwort = self.client.post(mit_id + "/analyse").raise_for_status().json()
            messung = auswertung.bewerte_ticket(self.werbung, self.roh, prompt, mock=False)
        self.assertEqual(antwort["ergebnis"], self.roh)
        self.assertEqual(messung["ki"], self.roh)
        self.assertEqual(antwort["tokens"], messung["tokens"])
        api, auswertung_aufruf = modell.call_args_list
        self.assertEqual(api.args, auswertung_aufruf.args)
        for aufruf in modell.call_args_list:
            self.assertEqual(aufruf.kwargs["temperatur"], 0)
            self.assertEqual(aufruf.kwargs["antwortformat"], app.ANALYSE_FORMAT)
            self.assertFalse(aufruf.kwargs.get("beratung"))
        system, nutzer = api.args[0]
        self.assertEqual(system["content"], prompt)
        self.assertIn(app.doku_abschnitt("bau", "Besonderheiten"), nutzer["content"])
        self.assertIn(self.werbung["beschreibung"], nutzer["content"])
        self.assertNotIn("regelhinweise", nutzer["content"])
        t = self.client.get(mit_id).json()
        self.assertEqual({feld: t["ki"][feld] for feld in self.roh}, self.roh)
        self.assertEqual(t["ki"]["modus"], "llama")
        self.assertEqual(t["prioritaet"], "hoch")
        self.assertFalse(eingang.ist_spam(t))

    def test_modellspam_wird_als_niedrig_und_spam_gespeichert_und_gemessen(self):
        roh = {**self.roh, "spam": True}
        erwartet = {**roh, "prioritaet": "niedrig", "kategorie": "Spam"}
        adr = f"/api/tickets/{self.werbung['id']}"
        with patch.object(app, "frage_llama", return_value=(json.dumps(roh), 10)):
            antwort = self.client.post(adr + "/analyse").raise_for_status().json()
            messung = auswertung.bewerte_ticket(self.werbung, erwartet, auswertung.PROMPTS["angepasst"], mock=False)
        ticket = self.client.get(adr).raise_for_status().json()
        self.assertEqual(antwort["ergebnis"], erwartet)
        self.assertEqual(messung["ki"], erwartet)
        self.assertEqual({k: ticket["ki"][k] for k in erwartet}, erwartet)
        self.assertEqual(ticket["prioritaet"], "niedrig")
        self.assertTrue(eingang.ist_spam(ticket))

    def test_neubewertung_von_spam_erhaelt_manuelle_entscheidung(self):
        roh = {**self.roh, "spam": True}
        adr = f"/api/tickets/{self.werbung['id']}"
        with patch.object(app, "frage_llama", return_value=(json.dumps(roh), 10)) as modell:
            for _ in range(2):
                self.client.post(adr + "/analyse").raise_for_status()
                self.assertTrue(eingang.ist_spam(self.client.get(adr).json()))
            self.client.patch(adr, json={"spam_entscheidung": "kein_spam", "prioritaet": "hoch"}).raise_for_status()
            self.client.post(adr + "/analyse").raise_for_status()
            self.assertEqual(modell.call_count, 3)
        t = self.client.get(adr).json()
        self.assertEqual(t["spam_entscheidung"], "kein_spam")
        self.assertFalse(eingang.ist_spam(t))
        self.assertEqual(t["prioritaet"], "hoch")
        self.assertEqual(t["prioritaet_quelle"], "manuell")
        self.assertEqual(t["ki"]["prioritaet"], "niedrig")

    def test_fehlerhafte_modellantwort_erzeugt_keine_einstufung(self):
        adr = f"/api/tickets/{self.werbung['id']}"
        for antwort in ("", "null", "[]", "{}", json.dumps({**self.roh, "spam": "Ja"}),
                        json.dumps({**self.roh, "prioritaet": "dringend"}),
                        json.dumps({**self.roh, "kategorie": "Büro"}),
                        json.dumps({**self.roh, "loesungsvorschlag": "fremdes Feld"})):
            with self.subTest(antwort=antwort), patch.object(app, "frage_llama", return_value=(antwort, 1)):
                self.assertEqual(self.client.post(adr + "/analyse").status_code, 502)
                self.assertIsNone(self.client.get(adr).json()["ki"])
