"""Modellidentität für die Anzeige in der lokalen Demo."""

import unittest
from unittest.mock import patch

import httpx

from backend import app


class ModellstatusTest(unittest.TestCase):
    def test_modellwahl_fuer_support_und_rohvergleich(self):
        ticket = {"kunde": "bau", "titel": "Fehlende Anzeige", "beschreibung": "Die Liste bleibt leer."}
        for aktiviert in (False, True):
            with self.subTest(aktiviert=aktiviert), patch.object(app, "SUPPORT_MIT_BERATUNGSMODELL", aktiviert), \
                    patch.object(app, "frage_llama", side_effect=[
                        ('{"prioritaet":"mittel","kategorie":"Software","beleg":1}', 20),
                        ('{"prioritaet":"mittel","kategorie":"Software","spam":false,"begruendung":"Liste fehlt."}', 25),
                    ]) as modell:
                app.analysiere_llama(ticket, nur_support=True)
                app.analysiere_llama(ticket)
                self.assertEqual([aufruf.kwargs.get("beratung", False) for aufruf in modell.call_args_list],
                                 [aktiviert, False])

    def test_anzeigename_gehoert_zum_ausgewaehlten_modell(self):
        def antwort(url, **kwargs):
            if url.endswith("/health"):
                daten = {}
            elif url.startswith(app.LLAMA_URL + "/"):
                daten = {"model_alias": "chat", "model_path": r"C:\modelle\chatmodell.gguf"}
            else:
                daten = {"model_alias": "anderes-modell", "model_path": "/modelle/anderes.gguf"}
            return httpx.Response(200, json=daten, request=httpx.Request("GET", url))

        with patch.object(app, "KI_MOCK", False), patch.object(app, "LLAMA_MODEL", "chat"), \
                patch.object(app, "EMBED_MODEL", "suche"), patch.object(app.httpx, "get", side_effect=antwort):
            status = app.status(modelldetails=True)
        self.assertEqual(status["chat_datei"], "chatmodell.gguf")
        self.assertNotIn("embedding_datei", status)
        self.assertTrue(status["embedding_erreichbar"])

    def test_separates_beratungsmodell_wird_nur_fuer_beratung_genutzt(self):
        def antwort(url, **optionen):
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]},
                                  request=httpx.Request("POST", url))

        with patch.object(app, "BERATUNG_URL", "http://127.0.0.1:8082"), \
                patch.object(app, "BERATUNG_MODEL", "beratung"), patch.object(app, "LLAMA_MODEL", "bewertung"), \
                patch.object(app.httpx, "post", side_effect=antwort) as senden:
            app.frage_beratungsmodell([])
            app.frage_llama([])
        self.assertEqual([(c.args[0], c.kwargs["json"]["model"]) for c in senden.call_args_list], [
            ("http://127.0.0.1:8082/v1/chat/completions", "beratung"),
            (f"{app.LLAMA_URL}/v1/chat/completions", "bewertung"),
        ])
