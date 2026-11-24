"""Ticketberatung über denselben Endpunkt wie im Dashboard; alle Daten bleiben im Test."""

import json
import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import app


class TicketfragenTest(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.tickets = app.lade_json(app.DATEN / "tickets.json")
        testdaten = Path(stack.enter_context(TemporaryDirectory()))
        stack.enter_context(patch.object(app, "wissensbasis", app.rag.Wissensbasis(testdaten / "wissen.json")))
        stack.enter_context(patch.object(app, "einbetter", app.rag.Einbetter("", mock=True)))
        stack.enter_context(patch.object(app, "lade_tickets", return_value=self.tickets))
        stack.enter_context(patch.object(app, "KI_MOCK", True))
        self.client = stack.enter_context(TestClient(app.app))

    def frage(self, nr, text, vorher=None, *, verlauf=()):
        r = self.client.post(f"/api/tickets/{nr}/frage", json={
            "frage": text, "vorherige_frage": vorher, "verlauf": verlauf})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_arbeitsanleitung_vergleichsfall_und_keine_livedaten(self):
        r = self.frage(1021, "Müssen wir etwas tun?")
        self.assertIn("Prüfe zeitnah die Belegung", r["antwort"])
        self.assertIn("archiviert", r["antwort"])
        self.assertNotIn("Arbeitsplätze", r["antwort"])
        self.assertIn("Im früheren Ticket #1020", r["antwort"])
        self.assertEqual(r["quellen"][1]["ticket_id"], 1020)
        self.assertIn("vorgehen", r["quellen"][0]["quelle"])
        self.assertTrue(r["quellen"][0]["links"][0]["url"].startswith("https://learn.microsoft.com/"))
        r = self.frage(1021, "Wie viel Speicher ist aktuell frei?")
        self.assertTrue(r["antwort"].startswith("Der Assistent hat keinen Zugriff auf aktuelle Messwerte"))

    def test_anleitung_bei_anderer_nummer_und_fremder_fall_geschuetzt(self):
        t = next(t for t in self.tickets if t["id"] == 1021)
        t["id"] = 9999
        fall = next(t for t in self.tickets if t["id"] == 1020)
        fall["kunde"] = "bau"
        r = self.frage(9999, "Was ist der nächste Schritt?")
        self.assertIn("Belegung", r["antwort"])
        self.assertNotIn("1020", r["antwort"])
        self.assertFalse(any(q.get("ticket_id") for q in r["quellen"]))
        self.assertIn("vorgehen", r["quellen"][0]["quelle"])
        self.assertIn("Wikipedia", r["quellen"][1]["quelle"])
        self.assertNotIn("damals", self.frage(9999, "Welcher frühere Fall passt?")["antwort"])

    def test_historie_anschlussfrage_und_andere_themen(self):
        r = self.frage(1021, "Gibt es einen ähnlichen gelösten Fall?")
        self.assertIn("Online-Archiv", r["antwort"])
        self.assertEqual([q["ticket_id"] for q in r["quellen"]], [1020])
        r = self.frage(1021, "Wie genau?", "Müssen wir etwas tun?")
        self.assertIn("Prüfe zeitnah die Belegung", r["antwort"])
        r = self.frage(1021, "Wie hoch ist die CPU-Temperatur?")
        self.assertNotIn("Postfach", r["antwort"])
        self.assertFalse(r["quellen"])

    def test_begriff_fakten_zugangsdaten_und_kundengrenze(self):
        r = self.frage(1021, "Was ist ein VPN?")
        self.assertEqual(r["modus"], "wikipedia")
        self.assertTrue(r["quellen"][0]["quelle"].startswith("Wikipedia"))
        r = self.frage(1021, "Welche IP hat das Gateway?")
        self.assertIn("192.168.50.1", r["antwort"])
        self.assertNotIn("Konnektor", r["antwort"])
        self.assertIn("Passwortmanager", self.frage(1021, "Passwort für den Server-Admin?")["antwort"])
        self.assertFalse(self.frage(1021, "Welches Gateway verwendet das Autohaus?")["quellen"])
        r = self.client.post("/api/tickets/1010/frage", json={"frage": "Was soll ich tun?"})
        self.assertEqual(r.status_code, 409)

    def test_fehlender_fall_und_bestaetigter_verweis(self):
        with patch.object(app, "erzeuge_vorschlag", return_value={
            "modus": "llama", "tokens": 8, "ergebnis": {"vorschlaege": []}
        }) as suche:
            r = self.frage(1023, "Was soll ich tun?")
            self.assertIn("keinen belegten Lösungsweg", r["antwort"])
            self.assertEqual(r["quellen"], [])
            self.assertTrue(suche.call_args.kwargs["nur_ticketkunde"])

    def test_action_auch_im_expliziten_dokumodus(self):
        t = next(t for t in self.tickets if t["id"] == 1021)
        r = self.client.post("/api/kunden/praxis/doku/suche", json={"frage": t["beschreibung"]}).json()
        self.assertIn("Prüfe zeitnah die Belegung", r["antwort"])
        self.assertNotIn("Arbeitsplätze", r["antwort"])

    def test_stoerung_verknuepft_aktenwissen_technik_und_vorfall(self):
        ticket = next(t for t in self.tickets if t["id"] == 1017)
        for frage in (ticket["beschreibung"], "Kanzleisoftware startet wieder nicht",
                      "Seit dem Reboot kommt keiner mehr in die Anwendung. Was prüfe ich zuerst?"):
            with self.subTest(frage=frage):
                r = self.frage(1017, frage)
                self.assertIn("STB-SRV01", r["antwort"])
                self.assertIn("protokoll", r["antwort"].lower())
                self.assertIn("Damaliger Lösungsweg", r["antwort"])
                self.assertIn("Ob dieselbe Ursache vorliegt", r["antwort"])
                self.assertEqual({q["ticket_id"] for q in r["quellen"] if "ticket_id" in q}, {1016})
                self.assertTrue(any(q["quelle"].startswith("doku/steuerbuero") for q in r["quellen"]))
                self.assertTrue(any(q.get("pruefschritte") for q in r["quellen"]))

    def test_neuer_befund_aendert_den_naechsten_schritt(self):
        r = self.frage(1017, "Der Dienst läuft bereits. Was prüfe ich jetzt?")
        self.assertIn("protokoll", r["antwort"].lower())
        self.assertNotIn("Status der", r["antwort"])
        self.assertNotIn("Damaliger Lösungsweg", r["antwort"])
        vpn = self.frage(1026, "Der VPN-Client zeigt jetzt verbunden. Nur die Freigabe ist nicht erreichbar.")
        self.assertIn("interne Ressource", vpn["antwort"])
        self.assertNotIn("Firmenprofil", vpn["antwort"])
        drucker = self.frage(1002, "Die Warteschlange ist jetzt leer, auf dem Papier kommt nichts an.")
        self.assertIn("Drucker selbst", drucker["antwort"])
        self.assertNotIn("Öffne die Warteschlange", drucker["antwort"])
        vpn = self.frage(1026, "Der Laptop baut keinen Tunnel auf. Im Client steht Verbindung fehlgeschlagen.")
        self.assertIn("Firmenprofil", vpn["antwort"])

    def test_konkrete_ki_formulierung_und_unbelegte_antworten(self):
        richtige_pruefung = "Kontrolliere auf STB-SRV01 den Status und den Starttyp der Dienstinstanz."
        for formulierung in [richtige_pruefung, "Starte den Datenbankserver neu.", "Prüfe den Status auf FAKE-SRV09."]:
            plan = json.dumps({"schritt": 0, "anweisung": formulierung, "rueckfrage": ""})
            with self.subTest(formulierung=formulierung), patch.object(app, "KI_MOCK", False), patch.object(
                    app, "frage_beratungsmodell", return_value=(plan, 40), create=True) as modell:
                r = self.frage(1017, "Was prüfe ich zuerst?")
                daten = json.loads(modell.call_args.args[0][1]["content"])
                self.assertIn("Starttyp", daten["frueherer_fall"]["damals"])
                self.assertTrue(any("STB-SRV01" in fakt for fakt in daten["kundenakte"]))
                self.assertTrue(daten["pruefungen"])
                self.assertEqual(r["tokens"], 40)
                if formulierung == richtige_pruefung:
                    self.assertIn(formulierung, r["antwort"])
                else:
                    self.assertNotIn(formulierung, r["antwort"])
                    self.assertIn("STB-SRV01", r["antwort"])

    def test_andere_kunden_und_offene_faelle_bleiben_ausgeschlossen(self):
        historisch = next(t for t in self.tickets if t["id"] == 1016)
        for kunde, status in [("bau", "geschlossen"), ("steuerbuero", "in_bearbeitung")]:
            historisch.update(kunde=kunde, status=status)
            r = self.frage(1017, "Kanzleisoftware zeigt wieder den Datenbankfehler.")
            self.assertNotIn("1016", json.dumps(r["quellen"]))
            self.assertNotIn("#1016", r["antwort"])

    def test_fehlende_fachnotiz_mit_konkreter_rueckfrage(self):
        text = "Tritt das Problem auch bei einer Testseite direkt am Gerät auf?"
        leer = {"modus": "llama", "tokens": None, "ergebnis": {"vorschlaege": []}}
        with patch.object(app, "KI_MOCK", False), patch.object(app, "erzeuge_vorschlag", return_value=leer):
            for frage in (text, "Welches Passwort steht im Passwortmanager?"):
                with self.subTest(frage=frage), patch.object(app, "frage_beratungsmodell", return_value=(
                        json.dumps({"rueckfrage": frage}), 25)):
                    r = self.frage(1027, "Die Etiketten bleiben leer, was ist der nächste Schritt?")
                    self.assertIn("Testseite", r["antwort"])
                    self.assertIn("Ursache ist offen", r["antwort"])
                    self.assertEqual(r["tokens"], 25)
                    self.assertNotIn("Passwort", r["antwort"])
                    if frage == text:
                        self.assertIn(text, r["antwort"])

    def test_angefragte_erstpruefung_konkretisierung_und_neuer_befund(self):
        fragen = ["Was ist der nächste Schritt?", "Was soll ich machen?"]
        start = self.frage(1008, fragen[0])
        self.assertEqual(start["modus"], "fachdialog")
        self.assertIn("Display", start["antwort"])
        self.assertNotIn("dialog", json.dumps(start["quellen"]))
        self.assertIn("Anmeldeplatz 1", start["antwort"])
        genauer = self.frage(1008, fragen[1], verlauf=fragen[:1])
        self.assertIn("Einlesen", genauer["antwort"])
        self.assertNotEqual(start["antwort"], genauer["antwort"])
        mit_befund = self.frage(1008, "Das Display leuchtet. Was soll ich machen?", verlauf=fragen)
        self.assertIn("Kartensymbol", mit_befund["antwort"])
        self.assertNotIn("Stromversorgung", mit_befund["antwort"])
        erneut = self.frage(1008, "Was jetzt?", verlauf=[*fragen, "Das Display leuchtet."])
        self.assertIn("Einstecken", erneut["antwort"])
        self.assertNotEqual(mit_befund["antwort"], erneut["antwort"])
        neuer = self.frage(1008, "Inzwischen bleibt das Display dunkel.", verlauf=["Das Display leuchtet."])
        self.assertIn("Stromversorgung", neuer["antwort"])
        hypothetisch = self.frage(1008, "Ist das Display dunkel?")
        self.assertNotIn("Stromversorgung", hypothetisch["antwort"])

    def test_unverstaendliche_eingabe_ohne_erneute_suche(self):
        with patch.object(app, "erzeuge_vorschlag", side_effect=AssertionError("Fallsuche")), \
                patch.object(app, "frage_beratungsmodell", side_effect=AssertionError("Modellaufruf")):
            for text in ("aaaa", "???", "asdf"):
                r = self.frage(1008, text, verlauf=["Das Display leuchtet."])
                self.assertEqual(r["modus"], "rueckfrage")
                self.assertEqual(r["quellen"], [])
                self.assertNotIn("Display", r["antwort"])
        self.assertFalse(app.ticketfragen.unverstaendlich("AAAA", "DNS-Einträge prüfen"))
        self.assertFalse(app.ticketfragen.unverstaendlich("0x80004005", "Systemfehler"))

    def test_wissensluecke_mit_geraetepruefung_statt_erledigtem_vergleich(self):
        r = self.frage(1031, "Was soll ich machen?")
        self.assertIn("Geräteübersicht", r["antwort"])
        self.assertIn("funktioniert laut Meldung am anderen Arbeitsplatz", r["antwort"])
        self.assertNotIn("Kartenterminal", r["antwort"])
        self.assertNotIn("Praxis", r["antwort"])
        monitor = self.frage(1007, "Was soll ich machen?")
        self.assertIn("Bildschirmmenü", monitor["antwort"])
        self.assertNotIn("Werkstattplaner", json.dumps(monitor))
        self.assertEqual(monitor["quellen"], [])

    def test_offene_diagnose_nutzt_modellschritt_zum_symptom(self):
        schritt = "Prüfe das Statussymbol in der Geräteübersicht am betroffenen Arbeitsplatz."
        with patch.object(app, "KI_MOCK", False), patch.object(app, "erzeuge_vorschlag", return_value={
                "modus": "llama", "tokens": 0, "ergebnis": {"vorschlaege": []}}), patch.object(
                app, "frage_beratungsmodell", return_value=(json.dumps({"pruefung": schritt, "rueckfrage": ""}), 18)):
            antwort = self.frage(1031, "Was soll ich machen?")
            self.assertTrue(antwort["antwort"].startswith(schritt))
            self.assertEqual(antwort["modus"], "modellvorschlag")

    def test_offener_modellvorschlag_mit_neuem_fachbegriff_und_gueltiger_herkunft(self):
        ticket = next(t for t in self.tickets if t["id"] == 1027)
        ticket.update(titel="Fußnote im Schriftstück verschoben",
                      beschreibung="Die Fußnote beginnt in der Mitte der Seite. Im anderen Dokument steht sie unten.")
        rfrage = "Welchen Abstand zeigt der Absatzdialog in den beiden Fußnoten?"
        schritt = "Vergleiche die Absatzformatierung der verschobenen Fußnote mit der im zweiten Dokument."
        for vorschlag, modus in [
                (schritt, "modellvorschlag"), ("", "modellrueckfrage"),
                ("Prüfe die Fußnote auf DOK-SRV99.", "standardpruefung"),
                ("Prüfe die Fußnote und lösche die Formatvorlage.", "standardpruefung")]:
            with self.subTest(vorschlag=vorschlag), patch.object(app, "KI_MOCK", False), patch.object(
                    app, "erzeuge_vorschlag", return_value={"ergebnis": {"vorschlaege": []}, "tokens": 0}), patch.object(
                    app, "frage_beratungsmodell", return_value=(
                        json.dumps({"pruefung": vorschlag, "rueckfrage": rfrage}), 33)) as modell:
                r = self.frage(1027, "Was soll ich machen?", verlauf=["Beide Seiten sind gleich groß."])
                eingabe = json.loads(modell.call_args.args[0][1]["content"])
                self.assertEqual(eingabe["fruehere_nachrichten"], ["Beide Seiten sind gleich groß."])
                self.assertNotIn("moegliche_pruefung", eingabe)
                self.assertEqual(modus, r["modus"])
                self.assertEqual(r["quellen"], [])
                self.assertEqual(r["tokens"], 33)
                if modus == "modellvorschlag":
                    self.assertIn(schritt, r["antwort"])
                    self.assertIn(rfrage, r["antwort"])
                elif modus == "modellrueckfrage":
                    self.assertEqual(rfrage, r["antwort"])
                else:
                    self.assertNotIn(vorschlag, r["antwort"])

    def test_meldung_ohne_betroffene_funktion(self):
        ticket = next(t for t in self.tickets if t["id"] == 1027)
        ticket.update(titel="IT-Problem", beschreibung="Seit heute geht es nicht mehr. Bitte dringend helfen.")
        with patch.object(app, "erzeuge_vorschlag", return_value={"ergebnis": {"vorschlaege": []}, "tokens": 0}), \
                patch.object(app, "frage_beratungsmodell", side_effect=AssertionError("kein konkretes Symptom")):
            r = self.frage(1027, "Was soll ich machen?")
        self.assertEqual(r["modus"], "rueckfrage")
        self.assertIn("welcher Anwendung", r["antwort"])

    def test_lesender_modelltest_mit_vorschau_und_hypothese(self):
        ticket = next(t for t in self.tickets if t["id"] == 1027)
        ticket.update(titel="Abstand im Dokument", beschreibung="Vor einer Fußnote bleibt eine Lücke.")
        plan = {"erfolgreiche_gegenprobe": "", "fehlerbild": "Abstand vor der Fußnote",
                "hypothese": "Eine abweichende Formatierung könnte vor dem Absatz zusätzlichen Platz vorsehen.",
                "pruefung": "In der Vorschau die betroffene Fußnote ohne Speichern mit einer passenden Fußnote vergleichen. "
                            "Welcher Absatzabstand wird in der Formatierung der beiden Stellen angezeigt?",
                "rueckfrage": "Unterscheiden sich die Werte?"}
        with patch.object(app, "KI_MOCK", False), patch.object(app, "erzeuge_vorschlag", return_value={
                "ergebnis": {"vorschlaege": []}, "tokens": 0}), patch.object(
                    app, "frage_beratungsmodell", return_value=(json.dumps(plan), 70)):
            r = self.frage(1027, "Was kann ich prüfen?")
        self.assertEqual(r["modus"], "modellvorschlag")
        self.assertIn(plan["pruefung"], r["antwort"])
        self.assertIn("Mögliche Erklärung", r["antwort"])
        self.assertIn(plan["hypothese"], r["antwort"])

    def test_fachnotiz_verwendet_nur_explizit_zugeordnete_server(self):
        archiv = app.doku.Abschnitt("Software", "doku/beispiel.md#software",
                                    "Archivsoftware (Datenbank auf `ARCHIV-SRV03`)")
        zeit = app.doku.Abschnitt("Software", archiv.quelle, "Zeitbuchung (Datenbank auf `ZEIT-SRV02`)")
        anders = app.doku.Abschnitt("Software", archiv.quelle, "Zeitbuchung (Datenbank auf `ZEIT-SRV04`)")
        for text, fakten, erlaubter_host in [
                ("Rechnername funktioniert nicht, DNS-Auflösung schlägt fehl.", [archiv], None),
                ("Zeitbuchung meldet: Datenbank nicht erreichbar.", [archiv], None),
                ("Zeitbuchung meldet: Datenbank nicht erreichbar.", [archiv, zeit], "ZEIT-SRV02"),
                ("Zeitbuchung meldet: Datenbank nicht erreichbar.", [zeit, anders], None)]:
            ticket = {"titel": text, "beschreibung": text}
            nachweis = {}
            wissen = app.wiki.hintergrund(text)
            with self.subTest(text=text, ziel=erlaubter_host), patch.object(
                    app, "frage_beratungsmodell", side_effect=AssertionError("Anleitung bereits vorhanden")) as modell:
                antwort, quellen, tokens = app.ticketfragen.beratung(
                    ticket, "Was soll ich prüfen?", fakten, None, wissen, modell=modell, nachweis=nachweis)
            self.assertIsNone(tokens)
            self.assertEqual(nachweis["modus"], "fachnotiz")
            self.assertTrue(any(q.get("pruefschritte") for q in quellen))
            for host in ("ARCHIV-SRV03", "ZEIT-SRV02", "ZEIT-SRV04"):
                self.assertEqual(host in antwort, host == erlaubter_host)
                self.assertEqual(host in json.dumps(quellen), host == erlaubter_host)

    def test_client_und_datenbank_in_derselben_aktenzeile(self):
        text = "Zeitbuchung meldet: Datenbank nicht erreichbar."
        fakt = app.doku.Abschnitt("Software", "doku/beispiel.md#software",
                                  "Zeitbuchung (Client auf `BUERO-PC01`, Datenbank auf `ZEIT-SRV02`)")
        fall = {"id": 80, "titel": "Zeitbuchung gestört", "ursache": "Dienst beendet",
                "loesungsweg": "Dienst wieder verfügbar."}
        plan = {"schritt": 0, "anweisung": "Prüfe auf BUERO-PC01 den Status und Starttyp der Dienstinstanz.",
                "rueckfrage": "Welchen Status meldet BUERO-PC01?"}
        with patch.object(app, "frage_beratungsmodell", return_value=(json.dumps(plan), 32)) as modell:
            antwort, _, tokens = app.ticketfragen.beratung(
                {"titel": text, "beschreibung": text}, "Was soll ich prüfen?", [fakt], fall,
                app.wiki.hintergrund(text), modell=modell)
        self.assertEqual(tokens, 32)
        self.assertIn("ZEIT-SRV02", antwort)
        self.assertNotIn("BUERO-PC01", antwort)

    def test_schemazeichenlimit_zeigt_vollstaendige_saetze_und_einen_ehrlichen_rueckfall(self):
        def abgeschnitten(anfang, limit):
            text = anfang + " Wenn dagegen z. B. die Anzeige im Vergleich " + "erneut abweicht und " * 25
            return text[:limit - 7] + "untersc"

        erster = "Vergleiche den Ausdruck direkt am Drucker."
        frage = "Tritt das Problem auch bei einer Testseite direkt am Gerät auf?"
        angenommene_ursache = "Eine abweichende Vorschau könnte den leeren Ausdruck erklären."
        for pruefung, rueckfrage, modus in [
                (abgeschnitten(erster, 360), abgeschnitten(frage, 180), "modellvorschlag"),
                (abgeschnitten("Prüfe die Anzeige", 360), frage, "modellrueckfrage"),
                (abgeschnitten("Prüfe die Anzeige", 360), abgeschnitten("Wo erscheint z.B.", 180), "standardpruefung"),
                (erster.rstrip("."), "", "modellvorschlag")]:
            plan = {"pruefung": pruefung, "hypothese": abgeschnitten(angenommene_ursache, 180),
                    "rueckfrage": rueckfrage}
            with self.subTest(modus=modus, pruefung=pruefung), patch.object(app, "KI_MOCK", False), patch.object(
                    app, "erzeuge_vorschlag", return_value={"ergebnis": {"vorschlaege": []}, "tokens": 0}), \
                    patch.object(app, "frage_beratungsmodell", return_value=(json.dumps(plan), 120)):
                r = self.frage(1027, "Was kann ich prüfen?")
            self.assertEqual(modus, r["modus"])
            self.assertNotIn("untersc", r["antwort"])
            self.assertNotIn("Wenn dagegen", r["antwort"])
            if modus == "modellvorschlag":
                self.assertIn(erster.rstrip("."), r["antwort"])
                self.assertIn(angenommene_ursache, r["antwort"])
                if rueckfrage:
                    self.assertIn(frage, r["antwort"])
            elif modus == "modellrueckfrage":
                self.assertEqual(frage, r["antwort"])

    def test_vollstaendiger_satz_genau_am_limit(self):
        satz = "Vergleiche die Vorschau, z. B. mit dem Ergebnis am anderen Arbeitsplatz."
        self.assertEqual(app.ticketfragen.vollstaendiges_feld(satz, len(satz)), satz)
        fragment = "Prüfe den Wert, z. B."
        self.assertEqual(app.ticketfragen.vollstaendiges_feld(fragment, len(fragment)), "")
