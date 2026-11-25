"""Prüft den Schalter RAG_MIT_URSACHE: gelöste Fälle optional mit Ursache einbetten."""

import tempfile
import unittest
from pathlib import Path

from backend import rag


FALL = {
    "id": 1020, "kunde": "praxis", "status": "geschlossen",
    "titel": "Keine externen E-Mails mehr",
    "beschreibung": "Von außen kommen keine Mails mehr an.",
    "ursache": "Postfach hat die Speichergrenze erreicht",
    "loesungsweg": "Postfach aufgeräumt und Archiv eingerichtet",
}
NEU = {
    "id": 1021, "kunde": "praxis", "status": "neu",
    "titel": "Warnung: Postfach fast voll",
    "beschreibung": "Outlook meldet, dass das Postfach fast voll ist. Speichergrenze bald erreicht?",
}


class FalltextTest(unittest.TestCase):
    def test_standard_ist_nur_das_problem(self):
        self.assertEqual(rag.fall_text(FALL), rag.ticket_text(FALL))

    def test_mit_ursache_haengt_die_ursache_an(self):
        text = rag.fall_text(FALL, mit_ursache=True)
        self.assertTrue(text.startswith(rag.ticket_text(FALL)))
        self.assertTrue(text.endswith("Ursache: Postfach hat die Speichergrenze erreicht"))

    def test_ohne_ursache_bleibt_der_text_gleich(self):
        fall = {**FALL, "ursache": "  "}
        self.assertEqual(rag.fall_text(fall, mit_ursache=True), rag.ticket_text(fall))

    def test_umschalten_berechnet_die_vektoren_neu(self):
        einbetter = rag.Einbetter("http://127.0.0.1:8081", mock=True)
        with tempfile.TemporaryDirectory() as ordner:
            wb = rag.Wissensbasis(Path(ordner) / "wissen.json")
            ohne = wb.vektoren([FALL], einbetter)[1020]
            mit = wb.vektoren([FALL], einbetter, mit_ursache=True)[1020]
            self.assertNotEqual(ohne, mit)
            self.assertEqual(wb.vektoren([FALL], einbetter)[1020], ohne)

    def test_ursache_verbindet_anderes_symptom(self):
        """Im Mock (Wortvergleich) steigt die Ähnlichkeit, wenn die Ursache mitzählt."""
        einbetter = rag.Einbetter("http://127.0.0.1:8081", mock=True)
        anfrage = einbetter.einbetten([rag.ticket_text(NEU)])[0]
        with tempfile.TemporaryDirectory() as ordner:
            wb = rag.Wissensbasis(Path(ordner) / "wissen.json")
            ohne = rag.aehnlichkeit(anfrage, wb.vektoren([FALL], einbetter)[1020])
            mit = rag.aehnlichkeit(anfrage, wb.vektoren([FALL], einbetter, mit_ursache=True)[1020])
        self.assertGreater(mit, ohne)


if __name__ == "__main__":
    unittest.main()
