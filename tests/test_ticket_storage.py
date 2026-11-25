"""Regressionstests für parallele Änderungen der lokalen Ticketdaten."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch

from fastapi import HTTPException

from backend import app


ANALYSE = {
    "prioritaet": "mittel",
    "spam": False,
    "kategorie": "Software",
    "begruendung": "Eine Person ist betroffen.",
}


class TicketSpeicherTest(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        tmp = Path(stack.enter_context(TemporaryDirectory()))
        daten = tmp / "testdaten"
        daten.mkdir()
        (daten / "tickets.json").write_text("[]", encoding="utf-8")
        stack.enter_context(patch.object(app, "DATEN", daten))
        stack.enter_context(patch.object(app, "LAUFZEIT_TICKETS", tmp / "laufzeit" / "tickets.json"))
        stack.enter_context(patch.object(app, "tickets_generation", 0))
        stack.enter_context(patch.object(app, "KI_MOCK", True))
        stack.enter_context(patch.object(app, "analysiere_mock", return_value=ANALYSE))

    def anlegen(self, titel="Outlook startet nicht"):
        return app.ticket_anlegen(app.NeuesTicket(titel=titel, beschreibung="Eine Person ist betroffen."))

    def fall(self):
        t = self.anlegen()
        return app.ticket_aendern(t["id"], app.TicketAenderung(
            status="geschlossen", ursache="Defektes Profil", loesungsweg="Profil erneuern"))

    def vorschlag(self, quelle):
        return {
            "ergebnis": {
                "passender_fall": True,
                "vorschlaege": [{
                    "ursache": quelle["ursache"],
                    "loesungsweg": quelle["loesungsweg"],
                    "tickets": [quelle["id"]],
                }],
                "hinweis": "",
            },
            "treffer": [{"id": quelle["id"], "aehnlichkeit": 0.9}],
        }

    def wartefunktion(self, ergebnis):
        begonnen = Event()
        fortfahren = Event()

        def warten(*_):
            begonnen.set()
            if not fortfahren.wait(timeout=5):
                raise AssertionError("Test hat den KI-Aufruf nicht freigegeben")
            return ergebnis

        return begonnen, fortfahren, warten

    def test_analyse_erhaelt_manuelle_prioritaet_neues_ticket_und_fallsuche(self):
        t = self.anlegen()
        quelle = self.fall()
        begonnen, fortfahren, warten = self.wartefunktion(ANALYSE)
        with patch.object(app, "analysiere_mock", side_effect=warten), ThreadPoolExecutor() as pool:
            analyse = pool.submit(app.ticket_analyse, t["id"])
            try:
                self.assertTrue(begonnen.wait(timeout=5))
                app.ticket_aendern(t["id"], app.TicketAenderung(
                    status="in_bearbeitung", zugewiesen_an="technik", prioritaet="sehr_hoch"))
                neu = self.anlegen("Neues Ticket während der Analyse")
                with patch.object(app, "erzeuge_vorschlag", return_value=self.vorschlag(quelle)):
                    app.loesungsvorschlag(t["id"])
            finally:
                fortfahren.set()
            self.assertEqual(analyse.result(timeout=5)["prioritaet_ticket"], "sehr_hoch")

        ergebnis = app.ticket(t["id"])
        self.assertEqual(ergebnis["zugewiesen_an"], "technik")
        self.assertEqual(ergebnis["status"], "in_bearbeitung")
        self.assertEqual(ergebnis["prioritaet_quelle"], "manuell")
        self.assertEqual(ergebnis["ki"]["prioritaet"], "mittel")
        self.assertEqual(ergebnis["ki"]["aehnliche_tickets"], [quelle["id"]])
        self.assertEqual(app.ticket(neu["id"])["titel"], neu["titel"])

    def test_fallsuche_erhaelt_gleichzeitige_analyse(self):
        t = self.anlegen()
        quelle = self.fall()
        begonnen, fortfahren, warten = self.wartefunktion(self.vorschlag(quelle))
        with patch.object(app, "erzeuge_vorschlag", side_effect=warten), ThreadPoolExecutor() as pool:
            lauf = pool.submit(app.loesungsvorschlag, t["id"])
            try:
                self.assertTrue(begonnen.wait(timeout=5))
                app.ticket_analyse(t["id"])
            finally:
                fortfahren.set()
            self.assertTrue(lauf.result(timeout=5)["gespeichert"])

        ki = app.ticket(t["id"])["ki"]
        self.assertEqual(ki["prioritaet"], "mittel")
        self.assertEqual(ki["aehnliche_tickets"], [quelle["id"]])

    def test_reset_verwirft_alte_analyse_auch_bei_wiederverwendeter_nummer(self):
        t = self.anlegen()
        begonnen, fortfahren, warten = self.wartefunktion(ANALYSE)
        with patch.object(app, "analysiere_mock", side_effect=warten), ThreadPoolExecutor() as pool:
            analyse = pool.submit(app.ticket_analyse, t["id"])
            try:
                self.assertEqual(app.ticket(t["id"])["ki"], None)
                self.assertTrue(begonnen.wait(timeout=5))
                self.assertEqual(app.testdaten_zuruecksetzen()["tickets"], 0)
                self.assertEqual(self.anlegen()["id"], t["id"])
            finally:
                fortfahren.set()
            with self.assertRaises(HTTPException) as fehler:
                analyse.result(timeout=5)
            self.assertEqual(fehler.exception.status_code, 409)
        self.assertIsNone(app.ticket(t["id"])["ki"])

    def test_fallsuche_verwirft_geaenderte_quelle(self):
        t = self.anlegen()
        quelle = self.fall()
        begonnen, fortfahren, warten = self.wartefunktion(self.vorschlag(quelle))
        with patch.object(app, "erzeuge_vorschlag", side_effect=warten), ThreadPoolExecutor() as pool:
            lauf = pool.submit(app.loesungsvorschlag, t["id"])
            try:
                self.assertTrue(begonnen.wait(timeout=5))
                app.ticket_aendern(quelle["id"], app.TicketAenderung(loesungsweg="Anderer Lösungsweg"))
            finally:
                fortfahren.set()
            with self.assertRaises(HTTPException) as fehler:
                lauf.result(timeout=5)
            self.assertEqual(fehler.exception.status_code, 409)
        self.assertIsNone(app.ticket(t["id"])["ki"])

    def test_paralleles_anlegen_vergibt_unterschiedliche_ticket_ids(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            neue = list(pool.map(self.anlegen, (f"Testticket {n}" for n in range(12))))
        ids = {t["id"] for t in neue}
        self.assertEqual(len(ids), 12)
        self.assertEqual({t["id"] for t in app.lade_tickets()}, ids)
