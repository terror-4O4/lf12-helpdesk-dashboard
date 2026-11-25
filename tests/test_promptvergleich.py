"""Regressionstests für den fairen Promptvergleich und die Berichtsausgabe."""

import io
import json
import sys
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend import app
from scripts import auswertung


class PromptvergleichTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.faelle = app.lade_json(app.DATEN / auswertung.VERGLEICHSDATEN)

    def test_zurueckgehaltene_tickets_decken_prioritaeten_ab(self):
        alte_tickets = app.lade_json(app.DATEN / "tickets.json")
        self.assertEqual(len({t["id"] for t in self.faelle}), len(self.faelle))
        self.assertTrue({t["id"] for t in self.faelle}.isdisjoint(t["id"] for t in alte_tickets))
        self.assertTrue({t["beschreibung"] for t in self.faelle}.isdisjoint(
            t["beschreibung"] for t in alte_tickets
        ))
        self.assertEqual(Counter(t["erwartet"]["prioritaet"] for t in self.faelle),
                         {prioritaet: 5 for prioritaet in app.PRIORITAETEN})
        for t in self.faelle:
            with self.subTest(ticket=t["id"]):
                self.assertEqual(set(t["erwartet"]), set(auswertung.FELDER))
                self.assertIn(t["erwartet"]["kategorie"], app.KATEGORIEN)
                self.assertIsInstance(t["erwartet"]["spam"], bool)

    def test_beide_prompts_haben_identischen_ticketkontext_und_messen(self):
        faelle = self.faelle[:2]
        erwartet = {t["id"]: t["erwartet"] for t in faelle}
        variante = list(auswertung.PROMPTS)
        aufrufe = []

        def antwort(nachrichten, antwortformat, temperatur, *, messung):
            aufrufe.append((nachrichten[0]["content"], nachrichten[1]["content"],
                            antwortformat, temperatur))
            messung.update(zeit_bis_erster_token_s=0.1, antwortzeit_s=0.3,
                           tokens_pro_s=42, tokens=9)
            return json.dumps({**faelle[0]["erwartet"], "begruendung": "Test"}), 9

        with patch.object(auswertung, "lade_modell", return_value=0.2) as lade_modell:
            with patch.object(app, "frage_llama", side_effect=antwort), redirect_stdout(io.StringIO()):
                laeufe = auswertung.teste_modell("testmodell", faelle, erwartet, variante)

        lade_modell.assert_called_once_with("testmodell")
        einfach, angepasst = auswertung.PROMPTS.values()
        self.assertEqual([aufruf[0] for aufruf in aufrufe], [einfach, angepasst, angepasst, einfach])
        self.assertEqual(aufrufe[0][1:], aufrufe[1][1:])
        self.assertEqual(aufrufe[2][1:], aufrufe[3][1:])
        self.assertEqual([aufruf[3] for aufruf in aufrufe], [0, 0, 0, 0])
        for lauf in laeufe:
            self.assertEqual([t["id"] for t in lauf["tickets"]], [t["id"] for t in faelle])
            self.assertEqual(auswertung.kennzahlen(lauf)["mittelwerte"]["zeit_bis_erster_token_s"], 0.1)
            self.assertEqual(auswertung.kennzahlen(lauf)["mittelwerte"]["tokens_pro_s"], 42)

    def test_offline_bericht_enthaelt_keine_modellmesswerte(self):
        with TemporaryDirectory() as verzeichnis:
            ziel = Path(verzeichnis)
            with patch.object(auswertung, "ZIEL", ziel), patch.object(
                auswertung, "REPO", ziel.parent
            ), patch.object(sys, "argv", ["auswertung.py", "--vergleich", "--mock"]), patch.object(
                app, "frage_llama"
            ) as modell, redirect_stdout(io.StringIO()):
                auswertung.main()
            modell.assert_not_called()
            datei, = ziel.glob("promptvergleich-mock-*.json")
            bericht = json.loads(datei.read_text(encoding="utf-8"))
            self.assertEqual(bericht["meta"]["modus"], "mock")
            self.assertEqual({lauf["variante"] for lauf in bericht["laeufe"]}, {"einfach", "angepasst"})
            for lauf in bericht["laeufe"]:
                self.assertEqual(len(lauf["tickets"]), len(self.faelle))
                self.assertTrue(all(wert is None for wert in lauf["kennzahlen"]["mittelwerte"].values()))
            self.assertIn("Die Simulation nutzt keinen Prompt", datei.with_suffix(".md").read_text(encoding="utf-8"))
