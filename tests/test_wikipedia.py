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

    def test_stoerungswissen_kommt_aus_ticket_und_rueckfrage(self):
        meldung = ("Seit dem Neustart am Samstag meldet die Warenwirtschaft in allen Filialen "
                   "einen Fehler beim Verbinden mit der Datenbank.")
        with patch("socket.socket.connect", side_effect=AssertionError("Netzwerkzugriff")):
            datenbank, = wiki.hintergrund(meldung, "Was soll ich zuerst prüfen?")
        self.assertIn("Datenbankserver", datenbank["titel"])
        self.assertIn("Status", datenbank["pruefschritte"][0])
        self.assertIn("Starttyp", datenbank["pruefschritte"][0])
        self.assertIn("protokoll", datenbank["pruefschritte"][1])
        self.assertIn("oldid=", datenbank["links"][0]["url"])
        self.assertEqual(urlsplit(datenbank["links"][1]["url"]).hostname, "learn.microsoft.com")
        self.assertNotIn("STB-SRV01", datenbank["pruefhinweis"])
        anderes_thema = wiki.hintergrund(meldung, "Welche Rolle spielt hier DNS?")
        self.assertIn("DNS", anderes_thema[0]["titel"])

    def test_symptom_aus_freier_sprache_und_grenzen_des_abgleichs(self):
        konto, _ = wiki.hintergrund("Das Postfach des Teams ist schon wieder voll.")
        self.assertEqual(konto["titel"], "Speicherkontingent")
        self.assertIn("Warnschwelle", konto["pruefschritte"][0])
        disk, = wiki.hintergrund("Der Dateiserver meldet eine Disk Quota.")
        self.assertNotIn("pruefhinweis", disk)
        quelle, = wiki.hintergrund("Am Drucker im Versand bleiben die Aufträge stehen.")
        self.assertEqual(quelle["titel"], "Druckwarteschlange")
        self.assertIn("Warteschlange", quelle["pruefschritte"][0])
        for text in ("Das Parkhaus ist voll.", "Welchen Drucker sollen wir kaufen?",
                     "Seit einem Neustart am Wochenende erscheint eine Meldung.",
                     "Die Warteschlange am Empfang ist lang.", "Wie funktioniert DNSSEC?"):
            with self.subTest(text=text):
                self.assertEqual(wiki.hintergrund(text), [])

    def test_begriffsauskunft_und_pruefschritt_bleiben_unterscheidbar(self):
        quelle, = self.frage("Was ist ein Datenbankserver?")["quellen"]
        self.assertNotIn("pruefschritte", quelle)
        self.assertEqual(len(quelle["links"]), 1)

    def test_dns_und_mfa_in_alltagssprache_ohne_kundenzustand(self):
        meldungen = [
            ("Das Intranet ist per IP erreichbar, über den Namen geht es nicht.", "nslookup"),
            ("Neues Diensthandy, die Authenticator-App ist noch nicht eingerichtet.", "registriert"),
            ("Bei der Anmeldung kommt kein Bestätigungscode an.", "alternative Methode"),
        ]
        for meldung, erwartung in meldungen:
            with self.subTest(meldung=meldung):
                quelle, = wiki.hintergrund(meldung)
                self.assertIn(erwartung, quelle["pruefhinweis"])
                self.assertNotIn("192.168.", quelle["pruefhinweis"])
                self.assertNotIn("PX-SRV01", quelle["pruefhinweis"])
                self.assertIn("Microsoft", quelle["links"][1]["titel"])
        for frage in ("Was ist ein MX-Eintrag?", "Wofür ist MFA gut?"):
            quelle, = self.frage(frage)["quellen"]
            self.assertNotIn("pruefhinweis", quelle)
        self.assertEqual(wiki.hintergrund("Ich brauche ein neues Diensthandy."), [])
        self.assertEqual(wiki.hintergrund("Ich möchte den Namen im Adressbuch ändern."), [])

    def test_leere_frage_wird_abgewiesen(self):
        r = self.client.post("/api/wissen/wikipedia", json={"frage": "   "})
        self.assertEqual(r.status_code, 422)

    def test_freier_assistent_nutzt_fachwissen_ohne_kundenakte(self):
        with patch.object(app, "KI_MOCK", True), patch.object(
                app, "lade_tickets", side_effect=AssertionError("Unerwarteter Zugriff auf Kundenfälle")):
            def fragen(text):
                r = self.client.post("/api/ki/frage", json={"frage": text})
                self.assertEqual(r.status_code, 200)
                return r.json()

            begriff = fragen("Was bedeutet ein Speicherkontingent?")
            self.assertIn("Warnschwelle", begriff["antwort"])
            stoerung = fragen("Seit dem Serverneustart kommt keine Verbindung zur Datenbank zustande.")
            self.assertTrue(stoerung["quellen"])
            self.assertIn("protokoll", stoerung["antwort"].lower())
            self.assertNotIn("STB-SRV01", stoerung["antwort"])
            schritte = fragen("Was sind die nächsten Schritte bei einer Störung der Datenbank?")
            self.assertIn("protokoll", schritte["antwort"].lower())
            self.assertEqual(fragen("Wie lautet das Passwort für den Server?")["quellen"], [])
