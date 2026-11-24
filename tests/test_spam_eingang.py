"""Eingangsprüfung, Altstände und Entscheidungen des Supports über die HTTP-API."""

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import app, eingang, rag


class SpamEingangTest(unittest.TestCase):
    def setUp(self):
        self.pfad = Path(self.enterContext(TemporaryDirectory())) / "tickets.json"
        self.enterContext(patch.object(app, "LAUFZEIT_TICKETS", self.pfad))
        self.client = self.enterContext(TestClient(app.app))

    def test_eingang_prueft_alle_demo_tickets_vor_der_analyse(self):
        tickets = self.client.get("/api/tickets").json()
        soll = {t["id"]: t["spam"] for t in app.lade_json(app.DATEN / "erwartet.json")}
        uebung = app.lade_json(app.DATEN / "uebungstickets.json")
        soll.update({t["id"]: t["id"] == 1040 for t in uebung})
        self.assertCountEqual([t["id"] for t in tickets], list(soll))
        for t in tickets:
            with self.subTest(id=t["id"]):
                self.assertEqual(t["spampruefung"]["verdaechtig"], soll[t["id"]])
        for nr in (1003, 1009, 1010, 1011):
            t = self.client.get(f"/api/tickets/{nr}").json()
            self.assertTrue(t["spampruefung"]["begruendung"])
            with patch.object(app, "frage_llama") as modell:
                self.assertEqual(self.client.post(f"/api/tickets/{nr}/analyse").status_code, 409)
                self.assertEqual(self.client.get(f"/api/tickets/{nr}/aehnliche").status_code, 409)
                self.assertEqual(self.client.post(f"/api/tickets/{nr}/loesungsvorschlag").status_code, 409)
                modell.assert_not_called()

    def test_supportanliegen_ohne_kundenkennung_und_zitierte_werbung(self):
        werbung = next(t for t in app.lade_json(app.DATEN / "tickets.json") if t["id"] == 1010)
        mail = next(t for t in app.lade_json(app.DATEN / "tickets.json") if t["id"] == 1003)
        for titel, nachricht in [
            ("Bitte prüfen Sie diese Nachricht", "Wir haben eine verdächtige Mail erhalten. " + werbung["beschreibung"]),
            ("Anmeldung", "Mein Link zum Zurücksetzen funktioniert nicht. Ich kann das Passwort nicht eingeben."),
            ("Einkauf", "Bitte ein Angebot für zwei Ersatzbildschirme mit unserem vereinbarten Rabatt schicken."),
            ("Zwei neue Toner", "Laut Lieferantenangebot gilt der Rabatt auch heute. Dort steht „Jetzt bestellen“. Bitte die Bestellung für uns auslösen."),
            ("Weitergeleitete Nachricht", "Eine Kollegin hat die angehängte E-Mail bekommen. Können Sie diese Nachricht prüfen? " + mail["beschreibung"]),
            ("Katalog zum nächsten Wartungstermin", "Unser Katalog für Ersatzteile liegt bei. Der Techniker benötigt die Artikelnummern für Donnerstag."),
        ]:
            with self.subTest(titel=titel):
                r = self.client.post("/api/tickets", json={"titel": titel, "beschreibung": nachricht})
                self.assertEqual(r.status_code, 201)
                self.assertFalse(r.json()["spampruefung"]["verdaechtig"])
                self.assertIsNone(r.json()["ki"])
        # Ein absendender Kunde und ein geänderter Titel heben die inhaltlichen Indizien nicht auf.
        r = self.client.post("/api/tickets", json={
            "titel": "Nachricht an das Büro", "kunde": "praxis", "beschreibung": werbung["beschreibung"],
        })
        self.assertTrue(r.json()["spampruefung"]["verdaechtig"])

    def test_katalogwerbung_ohne_rabatt(self):
        r = self.client.post("/api/tickets", json={
            "titel": "Büromöbel im Herbst",
            "beschreibung": "Entdecken Sie die Schreibtische in unserem neuen Katalog. Bestellen Sie direkt in unserem Onlineshop.",
        })
        self.assertTrue(r.json()["spampruefung"]["verdaechtig"])
        self.assertIn("Sortiment", r.json()["spampruefung"]["begruendung"])

    def test_anzeigenangebot_und_kundenauftrag_im_eingang(self):
        for titel, text, werbung in [
            ("Mehr Reichweite", "Wir bieten Ihnen einen Anzeigenplatz für 120 Euro im Monat.", True),
            ("Stadtportal", "Sichern Sie sich einen Werbeplatz in unserem Branchenbuch.", True),
            ("Eintrag aktualisieren", "In unserem Branchenverzeichnis fehlt bei Ihrer Firma eine Telefonnummer. "
             "Können Sie uns den Ansprechpartner nennen?", False),
            ("Angefordertes Angebot", "Auf Ihre Anfrage senden wir das Angebot zu unserem Firmenverzeichnis. "
             "Buchen Sie den reservierten Anzeigenplatz für 120 Euro.", False),
            ("Unser Firmenverzeichnis zeigt den falschen Preis", "Beim Eintrag für die Messe stehen noch 99 Euro. "
             "Können Sie den Preis im CMS berichtigen?", False),
        ]:
            with self.subTest(titel=titel):
                r = self.client.post("/api/tickets", json={"titel": titel, "beschreibung": text})
                self.assertEqual(r.status_code, 201)
                t = r.json()
                self.assertEqual(t["spampruefung"]["verdaechtig"], werbung)
                self.assertEqual(t["spampruefung"].get("art"), "werbung" if werbung else None)
                if werbung:
                    self.assertEqual(self.client.post(f"/api/tickets/{t['id']}/analyse").status_code, 409)

    def test_neupruefung_hebt_nur_die_ausgewaehlte_freigabe_auf(self):
        for nr in (1010, 1003):
            self.assertEqual(self.client.patch(f"/api/tickets/{nr}", json={"spam_entscheidung": "kein_spam"}).status_code, 200)
        adr = "/api/tickets/1010"
        with patch.object(app, "KI_MOCK", True):
            self.assertEqual(self.client.post(adr + "/analyse").status_code, 200)
        alt = self.client.get(adr).json()
        self.assertEqual(alt["spam_entscheidung"], "kein_spam")
        self.assertEqual(alt["spampruefung"]["art"], "werbung")
        self.assertEqual(self.client.patch(adr, json={"spam_entscheidung": None}).status_code, 422)
        pruefung = {"spam_entscheidung": None, "erwartete_spam_entscheidung": "kein_spam", "erwarteter_status": alt["status"]}
        t = self.client.patch(adr, json=pruefung).json()
        self.assertTrue(eingang.ist_spam(t))
        self.assertIsNone(t["spam_entscheidung"])
        self.assertEqual(t["statushistorie"], alt["statushistorie"])
        self.assertEqual(self.client.patch(adr, json=pruefung).status_code, 409)
        self.assertEqual(self.client.post(adr + "/analyse").status_code, 409)
        self.assertEqual(self.client.get("/api/tickets/1003").json()["spam_entscheidung"], "kein_spam")

    def test_alter_fehlalarm_wird_entfernt_und_arbeitsstand_erhalten(self):
        alt = next(t for t in app.lade_json(app.DATEN / "tickets.json") if t["id"] == 1021)
        alt.update(prioritaet_quelle="manuell", prioritaet="hoch", zugewiesen_an="technik",
                   ki={"spam": True, "kategorie": "Spam", "prioritaet": "niedrig", "begruendung": "Alte Wertung",
                       "loesungsvorschlag": "Gespeicherter Hinweis", "aehnliche_tickets": [1002]})
        historie = alt["statushistorie"]
        self.pfad.write_text(json.dumps([alt]), encoding="utf-8")
        neu = self.client.get("/api/tickets/1021").json()
        self.assertFalse(neu["spampruefung"]["verdaechtig"])
        self.assertIsNone(neu["ki"]["kategorie"])
        self.assertEqual(neu["prioritaet"], "hoch")
        self.assertEqual(neu["prioritaet_quelle"], "manuell")
        self.assertEqual(neu["zugewiesen_an"], "technik")
        self.assertEqual(neu["statushistorie"], historie)
        self.assertEqual(neu["ki"]["aehnliche_tickets"], [1002])
        self.assertEqual(neu["ki"]["loesungsvorschlag"], "Gespeicherter Hinweis")
        self.assertEqual(json.loads(self.pfad.read_text(encoding="utf-8")), [neu])

    def test_manuelle_entscheidung_bleibt_auch_fuer_wissensbasis_verbindlich(self):
        adresse = "/api/tickets/1010"
        t = self.client.patch(adresse, json={"spam_entscheidung": "spam", "status": "geschlossen"}).json()
        self.assertEqual(t["status"], "geschlossen")
        self.assertFalse(rag.ist_fall(t))
        t = self.client.patch(adresse, json={"spam_entscheidung": "kein_spam", "status": "neu"}).json()
        self.assertFalse(eingang.ist_spam(t))
        self.assertTrue(t["spampruefung"]["verdaechtig"])
        with patch.object(app, "KI_MOCK", True):
            self.assertEqual(self.client.post(adresse + "/analyse").status_code, 200)
        t = self.client.patch(adresse, json={"status": "geschlossen", "loesungsweg": "Rückfrage geklärt."}).json()
        self.assertTrue(rag.ist_fall(t))
        self.assertIn(1010, self.client.get("/api/wissensbasis").json()["ids"])

    def test_konkurrierende_spampruefung_erfordert_aktuellen_status_und_entscheidung(self):
        adresse = "/api/tickets/1010"
        offen = {"erwarteter_status": "neu", "erwartete_spam_entscheidung": None}
        freigabe = {"spam_entscheidung": "kein_spam"}
        self.assertEqual(self.client.patch(adresse, json={**offen, **freigabe}).status_code, 200)
        # Die Entscheidung ist inzwischen anders, der Ticketstatus ist noch gleich.
        self.assertEqual(self.client.patch(adresse, json={
            **offen, "spam_entscheidung": "spam", "status": "geschlossen",
        }).status_code, 409)
        bestaetigung = self.client.patch(adresse, json={
            "erwarteter_status": "neu", "erwartete_spam_entscheidung": "kein_spam",
            "spam_entscheidung": "spam", "status": "geschlossen",
        }).json()
        # Weder die veraltete Ansicht noch ein unvollständiger Freigabeaufruf
        # dürfen eine geschlossene Nachricht ohne Lösungsweg zum Supportfall machen.
        for patchdaten, code in [
            ({**offen, **freigabe, "zugewiesen_an": "lena"}, 409),
            ({"erwarteter_status": "neu", "erwartete_spam_entscheidung": "spam", **freigabe, "status": "neu"}, 409),
            ({"erwarteter_status": "geschlossen", **freigabe}, 422),
            (freigabe, 422),
        ]:
            with self.subTest(patchdaten=patchdaten):
                self.assertEqual(self.client.patch(adresse, json=patchdaten).status_code, code)
                self.assertEqual(self.client.get(adresse).json(), bestaetigung)
        self.assertEqual(self.client.patch(adresse, json={
            "erwarteter_status": "geschlossen", "erwartete_spam_entscheidung": "spam",
            **freigabe, "status": "neu",
        }).status_code, 200)

    def test_spamentscheidung_waehrend_analyse_verhindert_spaetes_speichern(self):
        angefangen = Event()
        weiter = Event()

        def warten(_):
            angefangen.set()
            if not weiter.wait(5):
                raise RuntimeError("Testfreigabe fehlt")
            return {"prioritaet": "mittel", "kategorie": "Hardware", "spam": False, "begruendung": "Beispiel"}

        adresse = "/api/tickets/1007"
        with patch.object(app, "KI_MOCK", True), patch.object(app, "analysiere_mock", side_effect=warten):
            with ThreadPoolExecutor() as pool:
                lauf = pool.submit(self.client.post, adresse + "/analyse")
                try:
                    self.assertTrue(angefangen.wait(5))
                    r = self.client.patch(adresse, json={"spam_entscheidung": "spam", "status": "geschlossen"})
                    self.assertEqual(r.status_code, 200)
                finally:
                    weiter.set()
                self.assertEqual(lauf.result(timeout=5).status_code, 409)
        t = self.client.get(adresse).json()
        self.assertIsNone(t["ki"])
        self.assertEqual(t["spam_entscheidung"], "spam")
