import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from fastapi import HTTPException

from backend import app


NACHRICHT = [{"role": "user", "content": "Test"}]


def sse(*pakete: dict | str) -> str:
    return "".join(
        f"data: {json.dumps(paket) if isinstance(paket, dict) else paket}\n\n"
        for paket in pakete
    )


class LlamaMessungTest(unittest.TestCase):
    def test_sse_erfasst_erstes_ausgabesignal_und_server_tokenrate(self):
        antwort = sse(
            {"choices": [{"delta": {"role": "assistant"}}]},
            {"choices": [{"delta": {"reasoning_content": "Interner Start"}}]},
            {"choices": [{"delta": {"content": "Er"}}]},
            {"choices": [{"delta": {"content": "gebnis"}}]},
            {"choices": [{"finish_reason": "stop", "delta": {}}]},
            {"choices": [], "usage": {"completion_tokens": 7},
             "timings": {"predicted_per_second": 21.0}},
            "[DONE]",
        )

        def handler(anfrage):
            daten = json.loads(anfrage.content)
            self.assertTrue(daten["stream"])
            self.assertEqual(daten["stream_options"], {"include_usage": True})
            self.assertFalse(daten["cache_prompt"])
            self.assertEqual(daten["max_tokens"], 256)
            return httpx.Response(200, text=antwort, headers={"Content-Type": "text/event-stream"})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            def stream(method, url, *, trust_env, **optionen):
                self.assertFalse(trust_env)
                return client.stream(method, url, **optionen)

            uhr = SimpleNamespace(perf_counter=Mock(side_effect=[1.0, 1.25, 1.5, 1.75, 2.0]))
            with patch.object(app.httpx, "stream", stream), patch.object(
                app, "time", uhr,
            ):
                messung = {}
                self.assertEqual(app.frage_llama(NACHRICHT, messung=messung, max_tokens=256),
                                 ("Ergebnis", 7))
        self.assertEqual(messung, {
            "zeit_bis_erster_token_s": 0.25, "antwortzeit_s": 1.0,
            "tokens_pro_s": 21.0, "tokens": 7, "abschlussgrund": "stop",
        })

    def test_abgebrochener_stream_zaehlt_nicht_als_messwert(self):
        stream = sse({"choices": [{"delta": {"content": "Abbruch"}}]})
        antwort = httpx.Response(200, text=stream)
        with self.assertRaises(HTTPException) as fehler:
            app.llama_stream_lesen(antwort, 0.0, {})
        self.assertEqual(fehler.exception.status_code, 502)

    def test_antwort_ohne_messung_verwendet_bisherigen_json_aufruf(self):
        antwort = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
                                 json={"choices": [{"message": {"content": "OK"}}],
                                       "usage": {"completion_tokens": 1}})
        with patch.object(app.httpx, "post", return_value=antwort) as post:
            self.assertEqual(app.frage_llama(NACHRICHT), ("OK", 1))
        self.assertNotIn("stream", post.call_args.kwargs["json"])


if __name__ == "__main__":
    unittest.main()
