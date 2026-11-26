"""Browser müssen die Dashboard-Dateien vor jeder Wiederverwendung validieren."""

import unittest

from fastapi.testclient import TestClient

from backend.app import app


class FrontendCacheTest(unittest.TestCase):
    def test_dashboard_und_module_werden_mit_etag_validiert(self):
        with TestClient(app) as client:
            for pfad in ("/", "/index.html", "/css/style.css", "/js/app.js"):
                with self.subTest(pfad=pfad):
                    antwort = client.get(pfad)
                    self.assertEqual(antwort.status_code, 200)
                    self.assertEqual(antwort.headers.get("Cache-Control"), "no-cache")
                    erneut = client.get(pfad, headers={"If-None-Match": antwort.headers["ETag"]})
                    self.assertEqual(erneut.status_code, 304)
                    self.assertEqual(erneut.headers.get("Cache-Control"), "no-cache")

    def test_frontend_cache_header_gilt_nur_fuer_statische_dateien(self):
        with TestClient(app) as client:
            antwort = client.get("/api/kunden")
        self.assertEqual(antwort.status_code, 200)
        self.assertNotIn("Cache-Control", antwort.headers)
