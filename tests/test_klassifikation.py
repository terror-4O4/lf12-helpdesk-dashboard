"""Regressionen für den produktiven Supportpfad und dessen Ticketbelege."""

import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend import app, eingang, klassifikation


class SupportklassifikationTest(unittest.TestCase):
    def test_mail_zur_pruefung_bleibt_beim_fachgebiet_email(self):
        ticket = {"titel": "Hinweis für das Netzwerkteam",
                  "beschreibung": "Wir haben eine Mail erhalten. Könnt ihr die Mail prüfen?"}
        ticket["spampruefung"] = eingang.pruefe(ticket)
        self.assertFalse(ticket["spampruefung"]["verdaechtig"])
        wert = klassifikation.supportbewertung(ticket, {"prioritaet": "niedrig", "kategorie": "Netzwerk"})
        self.assertEqual(wert["kategorie"], "E-Mail")
        self.assertEqual(wert["bewertungsquellen"]["kategorie"], "regel")

    def bewerte(self, titel, text, modell_prio="hoch", modell_kat="Software"):
        return klassifikation.supportbewertung(
            {"titel": titel, "beschreibung": text},
            {"prioritaet": modell_prio, "kategorie": modell_kat,
             "begruendung": "Ein unbeteiligter Kunde wünscht einen Rückruf."},
        )

    def test_drei_gemeldete_faelle_mit_veraenderten_formulierungen(self):
        faelle = [
            ("Anschaffung eines Bildschirms im Vertrieb", "Bitte um ein Angebot.",
             "Hardware", "niedrig"),
            ("Hinweis im Postfach", "Das Postfach ist nahezu voll. Nachrichten kommen weiter an.",
             "E-Mail", "mittel"),
            ("Büroumzug", "Der geplante Termin ist flexibel.", "Sonstiges", "niedrig"),
        ]
        for titel, text, fach, stufe in faelle:
            with self.subTest(titel=titel):
                wert = self.bewerte(titel, text)
                self.assertEqual((wert["kategorie"], wert["prioritaet"]), (fach, stufe))
                self.assertEqual(wert["bewertungsquellen"], {"kategorie": "regel", "prioritaet": "regel"})
                self.assertNotIn("Rückruf", wert["begruendung"])

    def test_ersatzbeschaffung_bei_arbeitsausfall_und_berichteter_umgehung(self):
        ausfall = self.bewerte("Wunsch: Ersatzmonitor", "Mein Monitor ist kaputt. Ich kann nicht arbeiten.")
        self.assertEqual(ausfall["prioritaet"], "hoch")
        umgehung = self.bewerte("Bildschirm flackert", "Am geliehenen Gerät kann ich weiterarbeiten.")
        self.assertEqual(umgehung["prioritaet"], "mittel")
        self.assertIn("Am geliehenen Gerät", umgehung["begruendung"])
        akut = self.bewerte("Postfach nahezu voll", "Inzwischen ist kein Empfang möglich.")
        self.assertEqual(akut["prioritaet"], "hoch")
        self.assertEqual(akut["bewertungsquellen"]["prioritaet"], "regel")

    def test_mehrere_fachgebiete_und_fremder_modelltext(self):
        wert = self.bewerte("VPN und Drucker prüfen", "Nach unserer Umstellung gibt es Fehler.",
                            modell_kat="Netzwerk")
        self.assertEqual(wert["kategorie"], "Netzwerk")
        self.assertEqual(wert["bewertungsquellen"], {"kategorie": "modell", "prioritaet": "modell"})
        self.assertNotIn("Rückruf", wert["begruendung"])
        self.assertIn("VPN und Drucker prüfen", wert["begruendung"])

    def test_nur_fachlich_passende_eskalationsregeln(self):
        kunde = "- Rückrufe am besten morgen.\n- Fällt die Zeiterfassung aus, immer hohe Priorität."
        leer = {"titel": "Tausch einer Maus", "beschreibung": "Für einen Arbeitsplatz."}
        self.assertEqual(klassifikation.eskalationsregeln(kunde, leer), [])
        leer["titel"] = "Zeiterfassung öffnet sich nicht"
        self.assertEqual(len(klassifikation.eskalationsregeln(kunde, leer)), 1)

    def test_allgemeiner_betreff_verwendet_eindeutiges_fachgebiet_der_beschreibung(self):
        wert = self.bewerte("Störung seit der Mittagspause", "Der Etikettendrucker zeigt Papierstau.")
        self.assertEqual(wert["kategorie"], "Drucker")
        self.assertIn("Etikettendrucker", wert["begruendung"])

    def test_verneinter_ausfall_und_absprache_loesen_keine_eskalation_aus(self):
        wert = self.bewerte("Wartung abstimmen", "Es gibt keinen Ausfall.", modell_prio="niedrig")
        self.assertEqual(wert["prioritaet"], "niedrig")
        self.assertEqual(wert["bewertungsquellen"]["prioritaet"], "modell")
        weiter = self.bewerte("Versand vorbereiten", "Der Versand steht bereit.", modell_prio="niedrig")
        self.assertEqual(weiter["prioritaet"], "niedrig")

    def test_mehrere_plaetze_mit_ausweichplatz_und_negierte_umgehung(self):
        workaround = self.bewerte("Kein Zugriff im ganzen Büro",
                                  "Am Ersatzplatz funktioniert der Zugang vorübergehend.")
        self.assertEqual(workaround["prioritaet"], "mittel")
        fehlt = self.bewerte("Das Display bleibt dunkel", "Ich kann nicht weiterarbeiten.")
        self.assertEqual(fehlt["prioritaet"], "hoch")

    def test_supportschema_verwendet_originalstelle_und_verwirft_falsche_nummern(self):
        t = {"kunde": "bau", "titel": "Vorgang beendet sich", "beschreibung": "Die Liste bleibt leer."}
        def modell(zahl):
            return json.dumps({"kategorie": "Software", "prioritaet": "mittel", "beleg": zahl}), 15
        with patch.object(app, "frage_llama", return_value=modell(1)) as anfrage:
            ist, tokens = app.analysiere_llama(t, nur_support=True)
        anfrage.assert_called_once()
        self.assertEqual(tokens, 15)
        self.assertEqual(ist["beleg"], t["beschreibung"])
        self.assertNotIn("Baustellen", anfrage.call_args.args[0][1]["content"])
        self.assertEqual(anfrage.call_args.kwargs["max_tokens"], 96)
        schema = anfrage.call_args.kwargs["antwortformat"]["json_schema"]["schema"]
        self.assertEqual(list(schema["properties"]), ["kategorie", "prioritaet", "beleg"])
        self.assertNotIn("Spam", schema["properties"]["kategorie"]["enum"])
        self.assertEqual(schema["properties"]["beleg"]["enum"], [0, 1])
        self.assertNotIn("grammatik", anfrage.call_args.kwargs)
        for index in (True, 8, -1):
            with self.subTest(index=index), patch.object(app, "frage_llama", return_value=modell(index)):
                with self.assertRaises(HTTPException):
                    app.analysiere_llama(t, nur_support=True)
        with patch.object(app, "frage_llama", return_value=('{"prioritaet":"niedrig"', 96)) as anfrage:
            with self.assertRaises(HTTPException) as fehler:
                app.analysiere_llama(t, nur_support=True)
            self.assertEqual(fehler.exception.status_code, 502)
            self.assertEqual(anfrage.call_count, 2)

    def test_nur_bei_formatfehler_einen_kompakten_zweitversuch(self):
        t = {"kunde": "bau", "titel": "Zugang ausgefallen", "beschreibung": "Ich kann nicht arbeiten."}
        gueltig = '{"prioritaet":"hoch","kategorie":"Netzwerk","beleg":1}'
        for erster in (96, None):
            with self.subTest(erster=erster), patch.object(app, "SUPPORT_MIT_BERATUNGSMODELL", True), \
                    patch.object(app, "frage_llama", side_effect=[("{}", erster), (gueltig, 20)]) as anfrage:
                ergebnis, tokens = app.analysiere_llama(t, nur_support=True)
            self.assertEqual(ergebnis["beleg"], t["beschreibung"])
            self.assertEqual(tokens, 116 if erster is not None else None)
            a, b = anfrage.call_args_list
            self.assertIn("antwortformat", a.kwargs)
            self.assertIn('beleg ::= "0" | "1"', b.kwargs["grammatik"])
            self.assertNotIn("antwortformat", b.kwargs)
            self.assertTrue(a.kwargs["beratung"] and b.kwargs["beratung"])
            self.assertEqual((a.kwargs["max_tokens"], b.kwargs["max_tokens"]), (96, 96))
        for status in (502, 504):
            with self.subTest(status=status), patch.object(app, "frage_llama", side_effect=HTTPException(status)) as anfrage:
                with self.assertRaises(HTTPException) as fehler:
                    app.analysiere_llama(t, nur_support=True)
                self.assertEqual(fehler.exception.status_code, status)
                anfrage.assert_called_once()

    def test_betriebsausfall_braucht_einen_aktuellen_befund(self):
        for beschreibung in (
            "Falls die Produktion steht, wen muss ich anrufen? Im Moment ist alles in Ordnung.",
            "Am Montag stand die Fertigung. Damals hieß es: Die Produktion steht. Inzwischen läuft der Betrieb wieder normal.",
            "Das Team kann keine Sonderfarbe einstellen. Alle Vorgänge lassen sich normal abschließen.",
        ):
            with self.subTest(beschreibung=beschreibung):
                wert = self.bewerte("Hinweis für das nächste Update", beschreibung, modell_prio="niedrig")
                self.assertEqual(wert["prioritaet"], "niedrig")

    def test_auswirkung_von_anderen_beobachtungen_trennen(self):
        text = ("Die Auftragsannahme ist an allen drei Stationen ausgefallen. "
                "Die Kaffeemaschine nebenan läuft weiter.")
        kritisch = self.bewerte("Störung in der Frühschicht", text, modell_prio="niedrig")
        self.assertEqual(kritisch["prioritaet"], "sehr_hoch")
        self.assertIn("an allen drei Stationen ausgefallen", kritisch["begruendung"])
        einzel = self.bewerte("Zugriff nicht möglich", "Ich kann nicht mehr arbeiten. "
                             "Alle Sachbearbeiter haben eine Rundmail erhalten. Die Telefonanlage läuft weiter.")
        self.assertEqual(einzel["prioritaet"], "hoch")

    def test_nur_ein_brauchbarer_ersatzweg_mindert_den_ausfall(self):
        for ersatz in ("Vielleicht könnte ich mit dem Ersatzgerät weiterarbeiten.",
                       "Der Ersatzplatz funktioniert ebenfalls nicht."):
            with self.subTest(ersatz=ersatz):
                wert = self.bewerte("Freigabe", "Ich kann nicht mehr arbeiten. " + ersatz, modell_prio="niedrig")
                self.assertEqual(wert["prioritaet"], "hoch")
        arbeitet = self.bewerte("Fehler beim Abgleich", "Die Synchronisation ist ausgefallen. "
                                "Wir können die Buchungen vorübergehend manuell übertragen.",
                                modell_prio="niedrig")
        self.assertEqual(arbeitet["prioritaet"], "mittel")
        self.assertEqual(arbeitet["bewertungsquellen"]["prioritaet"], "regel")

    def test_auf_wunsch_im_fehlerbericht_ist_keine_beschaffung(self):
        wert = self.bewerte("Bilder fehlen", "Der Kollege schickt sie auf Wunsch per Mail.",
                            modell_prio="mittel")
        self.assertEqual(wert["prioritaet"], "mittel")
        self.assertEqual(wert["bewertungsquellen"]["prioritaet"], "modell")

    def test_reiner_modellvergleich_uebernimmt_rohe_klassen(self):
        t = {"kunde": "bau", "titel": "Wunsch: neuer Monitor", "beschreibung": "Die Auswahl ist offen."}
        roh = {"kategorie": "Software", "prioritaet": "hoch", "spam": True, "begruendung": "Modelltext."}
        with patch.object(app, "frage_llama", return_value=(json.dumps(roh), 12)):
            ist, _ = app.analysiere_llama(t)
        self.assertEqual(ist, roh)
