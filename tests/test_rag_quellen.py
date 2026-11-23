"""Prüft, dass Lösungsvorschläge ausschließlich gespeicherte Quellen verwenden."""

import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend import app


NEUES_TICKET = {
    "id": 3,
    "kunde": "bau",
    "titel": "Druckauftrag bleibt stehen",
    "beschreibung": "Der Auftrag hängt in der Warteschlange.",
}
FAELLE = [
    {
        "id": 1,
        "kunde": "bau",
        "titel": "Drucker reagiert nicht",
        "beschreibung": "Die Warteschlange arbeitet den Auftrag nicht ab.",
        "ursache": "Ein beschädigter Auftrag blockiert die Warteschlange.",
        "loesungsweg": "Den betroffenen Auftrag in der Warteschlange löschen.",
    },
    {
        "id": 2,
        "kunde": "bau",
        "titel": "Aufträge stauen sich",
        "beschreibung": "Mehrere Aufträge stehen auf ausstehend.",
        "ursache": "Die Warteschlange ist angehalten.",
        "loesungsweg": "Die Warteschlange fortsetzen.",
    },
]


class RagQuellenTest(unittest.TestCase):
    def test_modell_waehlt_quellen_und_backend_kopiert_gespeicherte_vorschlaege(self):
        with patch.object(app, "frage_llama", return_value=('{"tickets": [2, 1, 2]}', 9)) as modell:
            ergebnis, tokens = app.loesung_llama(NEUES_TICKET, FAELLE)

        self.assertEqual(tokens, 9)
        self.assertTrue(ergebnis["passender_fall"])
        self.assertEqual(ergebnis["vorschlaege"], [
            {"ursache": fall["ursache"], "loesungsweg": fall["loesungsweg"], "tickets": [fall["id"]]}
            for fall in (FAELLE[1], FAELLE[0])
        ])
        modell.assert_called_once()

    def test_leere_quellenauswahl_ergibt_keinen_vorschlag(self):
        with patch.object(app, "frage_llama", return_value=('{"tickets": []}', 4)):
            ergebnis, tokens = app.loesung_llama(NEUES_TICKET, FAELLE)

        self.assertEqual(tokens, 4)
        self.assertFalse(ergebnis["passender_fall"])
        self.assertEqual(ergebnis["vorschlaege"], [])

    def test_ungueltige_modellantwort_wird_abgelehnt(self):
        antworten = (
            "kein JSON", "null", '[1]', '{}', '{"tickets": 1}',
            '{"tickets": ["1"]}', '{"tickets": [1.0]}', '{"tickets": [true]}',
            '{"tickets": [1, 999]}', '{"tickets": [1, 2, 1, 2]}',
        )
        for antwort in antworten:
            with self.subTest(antwort=antwort), patch.object(app, "frage_llama", return_value=(antwort, 5)):
                with self.assertRaises(HTTPException) as fehler:
                    app.loesung_llama(NEUES_TICKET, FAELLE)
                self.assertEqual(fehler.exception.status_code, 502)
