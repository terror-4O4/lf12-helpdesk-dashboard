"""Fachwissen ist offline nutzbar und belegt ausschließlich allgemeine Begriffe."""

import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from backend import app, wiki


class WikipediaTest(unittest.TestCase):
    def setUp(self):
        self.client = self.enterContext(TestClient(app.app))

    def frage(self, text):
        r = self.client.post("/api/wissen/wikipedia", json={"frage": text})
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_fachfrage_ohne_externen_aufruf_und_ohne_modell(self):
        with patch("socket.socket.connect", side_effect=AssertionError("Netzwerkzugriff")), \
             patch.object(app, "frage_llama", side_effect=AssertionError("Modellaufruf")):
            wert = self.frage("Was bedeutet eigentlich ein Speicherkontingent?")
        self.assertEqual(wert["modus"], "wikipedia")
        self.assertIn("Warnschwelle", wert["antwort"])
        self.assertEqual(len(wert["quellen"]), 1)
        quelle = wert["quellen"][0]
        link = urlsplit(quelle["links"][0]["url"])
        self.assertEqual((link.scheme, link.hostname), ("https", "de.wikipedia.org"))
        self.assertIn("oldid=", link.query)
        self.assertIn("Disk Quota", quelle["quelle"])

    def test_abgrenzung_zu_offenen_kundendaten_und_fremden_begriffen(self):
        for text in ("Was ist das Passwort von unserem VPN?",
                     "Welche Adresse hat unser DNS-Server?",
                     "Wie voll ist das Postfach der Praxis jetzt?",
                     "Wie behebe ich den Absturz des Taschenrechners?",
                     "Was ist Mindfulness?"):
            with self.subTest(frage=text):
                self.assertEqual(self.frage(text)["quellen"], [])

    def test_begriffe_koennen_verglichen_werden(self):
        wert = self.frage("Was ist der Unterschied zwischen Spam und Phishing?")
        self.assertEqual([q["titel"] for q in wert["quellen"]], ["Spam", "Phishing"])
        self.assertTrue(all(q["text"] in wert["antwort"] for q in wert["quellen"]))
        self.assertEqual(wiki.suche("Anleitung für DNSSEC"), [])
        self.assertEqual(self.frage("VPN-Tunnel")["quellen"][0]["titel"], "Virtuelles privates Netzwerk (VPN)")

    def test_leere_frage_wird_abgewiesen(self):
        r = self.client.post("/api/wissen/wikipedia", json={"frage": "   "})
        self.assertEqual(r.status_code, 422)
