# Lokale KI im IT-Helpdesk

**Klasse:** 12BE15 · Lernfeld 12 · Projektdokumentation

**Projektgruppe:** Marlon G., Linus R., Ricardo H. und Jennan H.

**Stand:** 25. November 2026 · Genehmigter Projektantrag V2.1 · Technischer Stand 23890a1

**Termine:** Abgabe am 11. Dezember 2026 · Präsentation bis zum 16. Dezember 2026

Wer im Helpdesk ein neues Ticket öffnet, muss drei Fragen beantworten. Wie dringend ist die Störung? Gab es schon einmal einen vergleichbaren Fall? Welche Angaben zur Kundenumgebung helfen bei der Bearbeitung? Für diese Arbeit hat die Projektgruppe ein Dashboard mit lokalem Sprachmodell umgesetzt. Die Funktionen sind auf dem Schullaptop vorführbar. Ob die vorgesehene Mac-Konfiguration die vier Qualitätsziele erreicht, ist Gegenstand der ausstehenden Messung.

## 1 Auftrag und Projektumfeld

### Ausgangssituation und Nutzen

Eine Meldung wie „Postfach fast voll“ kann eine echte Supportanfrage oder eine unerwünschte Nachricht sein. Auch für die Dringlichkeit reicht der Betreff kaum aus. Solange E-Mails ankommen, kann die Praxis weiterarbeiten. Steht dagegen der Versand eines Unternehmens wegen leerer Etiketten still, ist ein ganzer Arbeitsablauf betroffen. Zur Bearbeitung braucht der Support den Nachrichtentext, die Auswirkungen und gegebenenfalls Angaben aus der Kundenakte. Diese Informationen sollen in der Ticketansicht zusammenkommen.

Der genehmigte Antrag V2.1 ordnet das Vorhaben dem Schwerpunkt „KI im Unternehmen“ zu. Ziel ist ein lokaler Schulprototyp für IT-Supportkräfte. Die Gruppe nutzt fiktive Kundenakten und Ticketdateien, sodass sich auch falsche Einstufungen und deren Folgen kontrolliert untersuchen lassen. Im Dashboard entscheidet der Support über die Priorität, den Abschluss und den tatsächlich anzuwendenden Lösungsweg.

### Umfang und Erfolgskriterien

Der Auftrag umfasst die Übersicht über offene Tickets und Wartezeiten, die Priorisierung, die Suche in gelösten Fällen und die Suche in der Kundenakte. Spamprüfung und Ticketberatung ergänzen diese vier Kernfunktionen. Für die Messung wurden die folgenden Kriterien aus dem Antrag auf die vorgesehenen Prüffälle übertragen.

| Gegenstand | Wann zählt ein Treffer? | Mindestziel |
|---|---|---|
| Priorität | Die vorgeschlagene Stufe entspricht der vorab festgelegten Sollpriorität. | 16 von 20 |
| Kundenakte | Die Antwort nennt die erwartete Fundstelle und zeigt den zugehörigen Beleg. | 9 von 11 vorbereiteten Fragen mit Fundstelle |
| Bekannter Lösungsfall | Die erwartete frühere Ticketnummer steht unter den ersten drei Vorschlägen. | 5 von 6 |
| Fehlende Fallhistorie | Das System meldet, dass kein geeigneter Fall vorliegt, und erfindet keine frühere Lösung. | 5 von 6 |

Alle vier Ziele verlangen mindestens 80 Prozent. Bei kleinen Testreihen ist der nächste ganze Treffer entscheidend. Vier von sechs richtigen Antworten würden beispielsweise nur rund 67 Prozent ergeben.

## 2 Planung, Ressourcen und Aufwand

### Phasen und nachprüfbarer Verlauf

Der Antrag sieht zunächst die Kernfunktionen und danach erweiterte Assistenzfunktionen vor. Die Gruppe organisiert Aufgaben über Trello und prüft Änderungen im gemeinsamen GitHub-Repository. Der Entwicklungsverlauf lässt sich an konkreten Ergebnissen nachvollziehen.

| Phase | Belegter Stand | Ergebnis oder nächster Termin |
|---|---|---|
| Daten und lokale Bereitstellung | 19.11.2026 | Datenformat, Backend, 30 Referenztickets, Mac-Dienst und Modellvergleich wurden im Repository festgehalten. |
| Bedienbare Grundversion | 20.11.2026 | Ticketbearbeitung, erste Dashboard-Oberfläche und Suche in gelösten Tickets wurden zusammengeführt. |
| Funktionsprüfung und Überarbeitung | 23.–25.11.2026 | Entwicklungstests, Rückmeldung zur Spamprüfung und Review führten zu einer gemeinsamen Modellbewertung und drei kleineren Pull Requests. |
| Zielsystem und Abgabe | Ausstehend | Gemma-Messung und Auswertung dokumentieren. Abgabe am 11.12., Präsentation bis 16.12.2026. |

Die Git-Daten belegen Ergebnisse und Reihenfolge. Für den abschließenden Zeitvergleich benötigt die Gruppe ihre ursprünglichen Zeitansätze und den tatsächlich erfassten Aufwand je Phase. Aus den Abständen zwischen zwei Commits lassen sich keine Personenstunden ableiten.

### Betriebsmittel und Wirtschaftlichkeit

Für Entwicklung und Vorführungen stehen ein Windows-Schullaptop und ein Mac Pro mit 96 GB Arbeitsspeicher zur Verfügung. Auf dem Laptop können Oberfläche, Datenverarbeitung und Fehlerfälle unabhängig vom Mac erprobt werden. Der Mac ist für die Qualitätsmessung mit dem größeren Modell vorgesehen. Marlon betreut laut Projektübersicht die Bereitstellung und das Code-Review. Der Gruppenzugang zum vorgesehenen Zielsystem erfolgt über den vereinbarten Tailscale-Zugang.

Die Nutzung vorhandener Hardware erspart eine eigene Anschaffung für den Prototyp. Aufwand entsteht weiterhin durch Einrichtung, Modellbetrieb, Tests und Auswertung. Eine betriebliche Kalkulation könnte die gemessenen Betriebsstunden mit Leistungsaufnahme und Strompreis sowie den dokumentierten Personalaufwand mit einem begründeten Stundensatz verrechnen. Für diesen Projektstand liegen weder gemessener Energieverbrauch noch belastbare Gesamtkosten vor. Auch eine Zeitersparnis im Support wäre erst mit einem Vergleich tatsächlich bearbeiteter Fälle belegbar.

## 3 Lösungsentwurf und technische Entscheidungen

### Systemaufbau

Der Browser zeigt das Dashboard und sendet Anfragen an das Python-Backend mit FastAPI. Das Backend liest die Ticket-Arbeitskopie und die Dokumente des gewählten Kunden. Je nach Frage übergibt es den erforderlichen Ausschnitt an den lokalen llama.cpp-Dienst. Ein zweiter Dienst berechnet Zahlenvektoren für die Ähnlichkeitssuche. Das Backend ordnet die Antwort dem Ticket zu und liefert sie zusammen mit ihrer Herkunft an die Oberfläche.

| Entscheidung | Abgewogene Möglichkeiten | Begründung |
|---|---|---|
| Speicherung | Lokale Dateien oder eigener Datenbankdienst | JSON-Dateien und Markdown-Akten erfüllen die Vorgabe der simulierten Ordnerablage. Bei einigen Dutzend Fällen ist der Bestand nachvollziehbar und lässt sich für Tests reproduzieren. |
| Modellbetrieb | Kleines Laptopmodell oder leistungsfähigeres Modell auf dem Mac | Der Laptop erlaubt frühe Funktionsprüfungen. Für vergleichbare Qualitätsmessungen dient Gemma 4 26B-A4B auf dem Mac als festgelegte Konfiguration. |
| Suche nach früheren Fällen | Gleiche Wörter zählen oder inhaltliche Ähnlichkeit berechnen | Kunden beschreiben denselben Fehler unterschiedlich. Im Modellbetrieb werden Vektoren verglichen. Eine Mindestähnlichkeit begrenzt unpassende Treffer. |
| Ticketbewertung | Wortmuster als Entscheidungsregel oder gemeinsames Modellurteil | Der Auftrag untersucht die Leistung der KI. Das Modell liefert Spamverdacht, Kategorie und Priorität. Zusätzliche Wortmuster erscheinen als eigene Hinweise. |

### Trennung der Datenbestände

Die Referenzbasis umfasst 30 Tickets und die zugehörigen Sollwerte. Zehn weitere Übungstickets stehen in einer eigenen Datei. Die Anwendung speichert während der Bearbeitung Änderungen in einer Arbeitskopie. Erwartete Ergebnisse gehören zur Auswertung und werden dem Modell bei der Ticketbewertung nicht als Antwort mitgegeben. Auf diese Weise bleibt der Ausgangsbestand für Wiederholungsläufe erhalten. [Datenformat und Beispieldaten](https://github.com/terror-4O4/lf12-helpdesk-dashboard/blob/23890a1/docs/datenformat.md)

## 4 Umsetzung und Bearbeitungsablauf

### Vom Ticket zum begründeten Vorschlag

Die Übersicht zeigt Status, Ticketalter und Wartezeit. Der Wechsel eines Tickets in einen neuen Status kann eine neue Wartephase beginnen. Das Ticketalter läuft seit der Erstellung weiter. Für die Reaktionsfrist berücksichtigt die Anzeige die Priorität. So kann der Support auch erkennen, dass eine Kundenantwort Aufmerksamkeit braucht, obwohl das Ticket schon länger existiert.

Bei der Analyse erhält das Modell den Betreff, die Beschreibung und die vorgesehenen Angaben zum Kunden. In einem Aufruf liefert es Priorität, Kategorie, Spamverdacht und eine kurze Begründung. Violette Markierungen mit Stern kennzeichnen Modellvorschläge. Der Support kann eine Priorität manuell ändern oder ein Ticket aus der Spamprüfung freigeben. Diese Entscheidungen bleiben bei einer erneuten Modellbewertung erhalten. Beim Speichern werden parallele Änderungen berücksichtigt. Ist die Berechnungsgrundlage inzwischen veraltet, kann die Anwendung einen Konflikt melden.

### Wie die Wissensbasis wächst

Beim Abschluss eines Supportfalls erfasst die bearbeitende Person Ursache und Lösungsweg. Die nächste Suche kann das geschlossene Ticket als Quelle heranziehen. Verglichen wird die Problembeschreibung. Fälle desselben Kunden erhalten bei der Sortierung einen Bonus. Anschließend wählt das Sprachmodell unter den passenden Kandidaten frühere Fälle aus. Angezeigt werden dokumentierte Ursachen und Lösungswege samt Ticketnummer. Unterhalb der Suchschwelle meldet das System den fehlenden Treffer.

Eine frühere Ursache ist ein Prüfhinweis für den neuen Fall. Beim erneuten Ausfall der Kanzleisoftware in Ticket 1017 kann der frühere Fall 1016 die Prüfung des Datenbankdienstes begründen. Der Bearbeiter muss am aktuellen System feststellen, ob der Dienst tatsächlich betroffen ist.

### Kundendokumentation und Ticketberatung

Die Aktensuche zeigt den Abschnitt und den Text, der eine Auskunft belegt. Bei einer Frage zum Netzwerk-Gateway ist etwa der Netzwerkteil der betreffenden Kundenakte relevant. Die Ticketberatung kann zusätzlich passende frühere Fälle und lokale IT-Fachnotizen heranziehen. Der Support sieht einen kurzen Prüfschritt und kann die Quellen öffnen. Reicht die Modellantwort fachlich nicht aus, kennzeichnet das Dashboard die verwendete Ersatzhilfe. Die lokal abgelegten Fachnotizen sind auch ohne Internet durchsuchbar. Zum Öffnen der externen Originalquelle wird eine Verbindung benötigt. [Herkunft und Lizenzen der Fachnotizen](https://github.com/terror-4O4/lf12-helpdesk-dashboard/blob/23890a1/data/wissen/README.md)

## 5 Qualitätssicherung und bisherige Ergebnisse

### Zwei Vergleiche mit festgelegten Sollwerten

Für die Priorisierung laufen dieselben 20 Prüftickets mit einem einfachen Prompt und dem Projektprompt v2 auf demselben Modell. Die Reihenfolge der Varianten wechselt je Ticket. Beim zweiten Vergleich bearbeitet dasselbe Modell Fälle mit und ohne Ticket-Historie. Die vier Qualitätsquoten werden getrennt ausgewiesen. Außerdem werden die Zeit bis zum ersten erzeugten Token, die vollständige Antwortzeit und die Ausgabegeschwindigkeit in Tokens pro Sekunde protokolliert. Modell, Rechner, Commit und Datum müssen zum jeweiligen Bericht gehören.

Promptanpassung und zusätzlich bereitgestellte Fallhistorie verändern die Informationen beim Modellaufruf. Die Modellgewichte bleiben dabei gleich. Der genehmigte Antrag sieht ein zusätzliches Nachtraining per LoRA als optionale Erweiterung vor. Ein solcher Trainingslauf ist für den beschriebenen Entwicklungsstand nicht belegt.

| Prüfung | Beobachtung | Aussage für die Abnahme |
|---|---|---|
| Automatisierte Tests am Stand aus PR 16 | 78 Python-Tests und 14 Oberflächentests bestanden. | Der getestete Ablauf funktioniert, einschließlich manueller Korrekturen und Quellenanzeige. |
| Doku-Suche im simulierten Betrieb am 23.11. | 11/11 erwartete Fundstellen, 4/4 korrekt gemeldete fehlende Treffer und 2/2 automatische Ticketabfragen. | Prüft die Suche und den Rückgabeweg mit simuliertem Modell. |
| Historische Fallsuche im selben simulierten Betrieb | 3/6 erwartete frühere Fälle gefunden, 6/6 Fälle ohne passende Referenz korrekt gemeldet. | Der einfache Wortvergleich verfehlte die Hälfte der positiven Fälle. Die beiden Teilquoten bleiben getrennt. |
| Reale Laptop-Stichprobe nach dem Review | Qwen erkannte die Tonerwerbung in Ticket 1010. Es stufte auch die legitime Postfachwarnung in Ticket 1021 als Spam ein. | Echter Fehlalarm. Beide Fälle sind für die Gegenprüfung auf dem Mac vorgemerkt. |

### Leistung und Grenzen der Übertragbarkeit

Ein früherer Windows-Versuch mit Qwen2.5 0.5B zeigt den Nutzen einer getrennten Qualitäts- und Laufzeitmessung. Der einfache Prompt erreichte 6 von 20 Sollprioritäten. Im Mittel dauerte es 0,945 Sekunden bis zum ersten Token und 3,370 Sekunden bis zur vollständigen Antwort, bei 39,2 Tokens pro Sekunde. Der damals angepasste Prompt erreichte 5 von 20, benötigte 4,587 bzw. 6,793 Sekunden und erzielte 35,4 Tokens pro Sekunde. In diesem Versuch erhöhte die damalige Anpassung die Wartezeit, ohne die Trefferquote zu verbessern. Dieser ältere Promptstand und das kleine Modell unterscheiden sich vom vorgesehenen Mac-Lauf. [Historisches Versuchsprotokoll](https://github.com/terror-4O4/lf12-helpdesk-dashboard/blob/3c44b88/docs/test-und-demo.md)

Für Gemma 4 26B-A4B am aktuellen Stand stehen alle vier Ergebnisse aus Abschnitt 1 noch aus. Für jede Quote wird der Zähler zusammen mit dem Nenner erfasst. Mindestens eine Fehlzuordnung wird anhand von Tickettext, Sollwert und Modellausgabe erläutert. Ein ausgefallener Serveraufruf zählt als fehlgeschlagener Prüffall. Der vorbereitete Ablauf umfasst außerdem den Test, ob ein gerade geschlossener Fall bei der nächsten Suche erscheint. [Prüfablauf und Auswertung](https://github.com/terror-4O4/lf12-helpdesk-dashboard/blob/23890a1/docs/test-und-demo.md)

## 6 Datenschutz und betriebliche Risiken

Tickettexte können Namen, Arbeitsabläufe und Zugangsdaten enthalten. Der Prototyp verwendet ausschließlich fiktive Kunden- und Ticketdaten. Die Kundenakten enthalten für Zugangsdaten Verweise auf einen Passwortmanager. Eine gezielte Frage nach einem Passwort soll genau diesen Verweis liefern. Das Backend prüft beim Start die konfigurierten Adressen der Modelldienste. Lokale Schlüssel und die veränderliche Ticketdatei sind von der Versionsverwaltung ausgenommen.

Für einen späteren Einsatz mit echten Kundendaten müsste der Betreiber Zweck und Rechtsgrundlage bestimmen, Berechtigungen pro Kunde durchsetzen und Löschfristen definieren. Eine Löschung müsste auch den Suchindex und gespeicherte Vorschläge erfassen. Für die Demo bildet die Sammlung gelöster Tickets einen gemeinsamen fiktiven Wissensbestand. Daraus ergibt sich für den Mehrkundenbetrieb eine konkrete Anforderung: Bereits bei der Auswahl der möglichen Quellen muss geprüft werden, ob die angemeldete Person auf sie zugreifen darf. Maßgeblich sind insbesondere die Grundsätze aus Art. 5, die Rechtsgrundlagen nach Art. 6 und angemessene Schutzmaßnahmen nach Art. 32 DSGVO. [Datenschutz und Projektrisiken](https://github.com/terror-4O4/lf12-helpdesk-dashboard/blob/23890a1/docs/datenschutz-und-risiken.md)

Auch ein lokales Modell kann ein dringendes Ticket übersehen oder eine unpassende Maßnahme vorschlagen. Die Kennzeichnung der Herkunft, eine sichtbare Fundstelle und der Vorrang manueller Entscheidungen machen solche Fehler prüfbar. Ob potenzielle Nutzer diese Hinweise verstehen, soll ein kurzer Bedienversuch zeigen. Dafür liegen Fragen zur Erkennbarkeit der KI-Priorität, zur Quellenanzeige und zur Passwortauskunft vor. Rückmeldungen aus diesem Versuch stehen noch aus.

## 7 Projektverlauf und Einsatz von KI-Werkzeugen

Eine Planänderung entstand aus der Arbeit mit der Oberfläche. Die Projektgruppe meldete unter anderem, dass eine echte Postfachwarnung als Spam erschien und eine Monitoranfrage die Kategorie Software erhielt. Zur Verbesserung der Demo wurden feste Regeln ergänzt. Im anschließenden Review fiel auf, dass diese Regeln mehrere Felder der Modellantwort überschrieben. Damit maß das Auswertungsskript teilweise ein anderes Ergebnis als das, das die Supportkraft im Dashboard sah.

Die Gruppe veranlasste eine Überarbeitung. Dashboard und Messskript verwenden jetzt dieselbe Analysefunktion und den festgelegten Projektprompt v2. Zusätzliche Regeln liefern gesonderte Hinweise. Die ursprünglichen 30 Tickets und ihre Sollwerte wurden wiederhergestellt, zusätzliche Meldungen liegen in einer eigenen Übungsdatei. Ein Regressionstest stellt dem Werbehinweis bewusst ein abweichendes Modellurteil gegenüber. So lässt sich erkennen, ob ein späterer Umbau den ursprünglichen Fehler erneut einführt. [Review mit Änderungsbegründung](https://github.com/terror-4O4/lf12-helpdesk-dashboard/pull/13#pullrequestreview-6039278503)

Die Gruppe steuert die Arbeit über Prompts, entscheidet über Funktionsumfang und meldet Beobachtungen aus der Bedienung. Codex und Claude werden für Programmierung, Tests, Dokumentationsentwürfe und die Prüfung von Änderungen eingesetzt. Die Rückmeldung zur Postfachwarnung stammt aus der Projektarbeit der Gruppe. Der automatisierte Test prüft die technische Folge der Änderung. Der neue Lauf auf dem Zielgerät und die Rückmeldungen potenzieller Nutzer bilden eigenständige Nachweise. Aufgaben, Entscheidungen, eingesetzte Werkzeuge und Links zu den Ergebnissen werden im gemeinsamen Status-Issue fortgeschrieben. [Projektstatus und Beitragsnachweis](https://github.com/terror-4O4/lf12-helpdesk-dashboard/issues/17)

## 8 Soll-Ist-Vergleich, Übergabe und Fazit

Die Kernfunktionen des genehmigten Auftrags sind in der Vorführversion vorhanden. Ein Supportmitarbeiter kann ein Ticket bewerten lassen, die zugrunde liegende Kundenakte öffnen, frühere Lösungen prüfen und seine eigene Entscheidung speichern. Technisch am weitesten belegt sind die Bedienabläufe und die Trennung von Modellurteil, Regelhinweis und manueller Korrektur. Bei der fachlichen Zuverlässigkeit zeigt die Postfachwarnung, warum die Gruppe die Ergebnisse einzeln beurteilen muss.

Für das Review wurde der ursprüngliche Sammelvorschlag in drei aufeinander aufbauende Teile geteilt. Der erste enthält Kundenakte und Speicherung, der zweite die gemeinsame Modellbewertung und der dritte die Ticketberatung. Der dritte Branch enthält den vollständigen Teststand für den Mac. Eine Zusammenführung in den Hauptzweig und die Qualitätsabnahme auf dem Zielgerät sind für diesen Stand offen. [Kundenakte und Speicherung](https://github.com/terror-4O4/lf12-helpdesk-dashboard/pull/14) · [Modellbewertung](https://github.com/terror-4O4/lf12-helpdesk-dashboard/pull/15) · [Vollständiger Teststand](https://github.com/terror-4O4/lf12-helpdesk-dashboard/pull/16)

| Noch ausstehender Nachweis | Ergänzung für die Abgabefassung |
|---|---|
| Zielsystem und Qualitätsziele | Bericht des Gemma-Laufs mit Commit, Modell, Datum, vier Trefferquoten und Laufzeiten. Abweichungen je Ziel beurteilen. |
| Zeit und Ressourcen | Freigegebene Zeitplanung und erfassten Ist-Aufwand je Phase gegenüberstellen. Abweichungen anhand einer konkreten Entscheidung erklären. |
| Anwenderperspektive und Vorführung | Termin und Ergebnis des Zwischenberichts, Rückmeldungen zum Datenschutz sowie Beobachtungen aus dem Präsentationsprobelauf festhalten. |
| Bewertungsschwerpunkt | Die Auswahl des doppelt gewichteten Kriteriums durch die Gruppe dokumentieren. Die vorführbereite Oberfläche steht zur Wahl. |

Für die Übergabe liegen Startanleitung, Datenformat und Prüfablauf im Repository. Bei Änderungen an der Modelllogik ist derselbe Vergleich mit festgehaltenem Softwarestand zu wiederholen. So kann die Gruppe bei der Abgabe zeigen, welche Verbesserung sich in den Ergebnissen tatsächlich wiederfindet.

### Unterlagen und Quellen

- Projektauftrag LF12a/LF12b mit vorläufigem Bewertungsraster vom 18.11.2026 und von der Lehrkraft genehmigter Projektantrag V2.1. Beide Unterlagen liegen im gemeinsamen Schulprojektordner.
- [Einrichtung und Betrieb des geprüften Helpdesks](https://github.com/terror-4O4/lf12-helpdesk-dashboard/blob/23890a1/README.md) und [Auswertungsskripte](https://github.com/terror-4O4/lf12-helpdesk-dashboard/blob/23890a1/scripts/README.md).
- [IHK Darmstadt – Die Projektarbeit in den IT-Berufen](https://www.ihk.de/darmstadt/produktmarken/pruefungen/downloads/muther/it-hinweise-projektantrag-2551070) und [IHK Wiesbaden – Hinweise zur Dokumentation](https://www.ihk.de/wiesbaden/bildung/ausbildung/ausbildungspruefungen/pruefung-neuordnung-it-berufe-5580462). Die Hinweise dienen als Orientierung für Aufbau und Prozessdarstellung. Für die Bewertung des Schulprojekts gilt das schulische Raster.
