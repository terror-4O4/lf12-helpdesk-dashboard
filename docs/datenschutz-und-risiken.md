# Datenschutz und Projektrisiken

## Daten im Schulprototyp

Für Entwicklung, Tests und Vorführung nutzen wir erfundene Tickets, Kundenakten und Vergleichsfälle. Der Zweck ist die Erprobung der KI im IT-Support. Reale Kundendaten und Zugangsdaten bleiben aus Tickettexten, Fragen, Wissensbasis und Auswertungen heraus. Auch im Schulprojekt können Konten, IP-Adressen oder Zugriffsprotokolle der beteiligten Personen personenbezogen sein. [DSGVO, Art. 4 und Erwägungsgrund 30](https://eur-lex.europa.eu/eli/reg/2016/679/oj/deu/pdf)

## Rechtsgrundlagen bei einem betrieblichen Einsatz

Vor der Verarbeitung realer Tickets müsste der Verantwortliche für Ticketbearbeitung, KI-Analyse, Wissensbasis und etwaige Protokollierung jeweils Zweck, benötigte Daten, Rechtsgrundlage und Löschfrist bestimmen. Art. 5 DSGVO verlangt unter anderem Zweckbindung, Datenminimierung und Speicherbegrenzung. Art. 6 Abs. 1 Buchst. b kommt etwa infrage, wenn die Verarbeitung zur Erfüllung eines Vertrags mit der betroffenen Person erforderlich ist. Bei einem privaten Betreiber kommt nach Buchst. f ein berechtigtes Interesse mit Prüfung der Erforderlichkeit und Abwägung gegen die Interessen und Rechte der betroffenen Personen in Betracht. Die Prüfung hängt vom konkreten Einsatz ab. [DSGVO, Art. 5 und 6](https://eur-lex.europa.eu/eli/reg/2016/679/oj/deu/pdf) · [DSK zu KI und Datenschutz, Abschnitt 1.5](https://datenschutzkonferenz-online.de/media/oh/20240506_DSK_Orientierungshilfe_KI_und_Datenschutz.pdf)

Der Verantwortliche müsste Betroffene nach Art. 13 bzw. 14 informieren und Auskunft, Berichtigung und Löschung nach Art. 15 bis 17 umsetzen, soweit die jeweiligen Voraussetzungen vorliegen. Beim RAG-Verfahren wären dafür auch Referenzdateien, Suchindex und gespeicherte Ergebnisse zu berücksichtigen. Art. 25 und 32 betreffen datenschutzfreundliche Voreinstellungen und risikogerechte Schutzmaßnahmen. Eine Datenschutz-Folgenabschätzung nach Art. 35 ist vorab erforderlich, wenn die geplante Verarbeitung voraussichtlich ein hohes Risiko für betroffene Personen mit sich bringt. [DSGVO, Art. 13–17, 25, 32 und 35](https://eur-lex.europa.eu/eli/reg/2016/679/oj/deu/pdf) · [DSK zu RAG-Systemen, Abschnitte 3.3–3.7](https://www.datenschutzkonferenz-online.de/media/oh/DSK_OH_RAG.pdf)

Das Dashboard kennzeichnet KI-Ergebnisse als Vorschläge. Supportkräfte prüfen sie und können die Priorität ändern. Für einen betrieblichen Einsatz müsste dieser Entscheidungsspielraum auch im Arbeitsablauf gewährleistet sein. Art. 22 DSGVO betrifft ausschließlich automatisierte Entscheidungen mit rechtlicher Wirkung oder vergleichbar erheblicher Beeinträchtigung. [DSGVO, Art. 22](https://eur-lex.europa.eu/eli/reg/2016/679/oj/deu/pdf) · [DSK zu KI und Datenschutz, Abschnitt 1.6](https://datenschutzkonferenz-online.de/media/oh/20240506_DSK_Orientierungshilfe_KI_und_Datenschutz.pdf)

## Schutzmaßnahmen im Projekt

- **Lokale Verarbeitung.** Das Backend prüft beim Start die Adressen für Chat und Embeddings und verwendet für diese Aufrufe keine System-Proxys. Die Standardadresse des Dashboards ist lokal. Der geplante Zugang für die Projektgruppe läuft über Tailscale. Die tatsächliche Freigabe und die mitlaufenden Dienste werden beim Start der Mac-Version geprüft. [Backend-Anleitung](../backend/README.md)
- **Daten und Schlüssel.** Die Anwendung arbeitet mit einer eigenen Ticketdatei unter `data/laufzeit/`. Laufzeitdaten, Protokolle und `.env` sind in Git ausgenommen. Kundenakten enthalten bei Zugangsdaten Verweise auf den Passwortmanager. Die Auswertung prüft anhand eines erfundenen Falls, dass eine entsprechende Anfrage den hinterlegten Verweis liefert. [.gitignore](../.gitignore) · [Prüffälle für die Doku-Suche](../data/testdaten/fragen_doku.json)
- **Quellen und Berechtigungen.** Die Dokumentensuche begrenzt die Auswahl auf die jeweilige Kundenakte. Bei ähnlichen gelösten Tickets behandelt die Demo den fiktiven Datenbestand als gemeinsamen Wissenspool. In einem realen Mehrkundenbetrieb müsste der Server anhand der angemeldeten Person sowohl die Kundenakten als auch die Kandidaten der Fallsuche vor der Übergabe an das Modell filtern. Die Kundenauswahl im Dashboard dient der fachlichen Eingrenzung. [Backend für Kundendoku und Tickets](../backend/app.py) · [DSK zu RAG-Systemen, Abschnitt 3.3](https://www.datenschutzkonferenz-online.de/media/oh/DSK_OH_RAG.pdf)

## Nutzererwartungen im Review prüfen

Unsere Annahme für das Review ist, dass Supportkräfte überprüfbare Quellen, eine manuelle Korrektur und klare Grenzen für den Umgang mit Zugangsdaten erwarten. Die folgenden Fragen prüfen diese Annahme anhand fiktiver Tickets. Ergebnisse einer Befragung stehen noch aus. Im Review-Protokoll genügen die beobachtete Bedienhürde, ihr Auslöser und die beschlossene Änderung.

1. Erkennst du, welche Priorität die KI vorgeschlagen hat? Kannst du eine falsche Einstufung korrigieren und die Änderung anschließend prüfen?
2. Findest du zu einer Antwort den Dokumentabschnitt oder das frühere Ticket? Ist erkennbar, wenn keine belastbare Fundstelle vorliegt?
3. Was erwartest du als Ausgabe bei einer Passwortfrage? Welche Inhalte sollen bereits bei der Eingabe außen vor bleiben?
4. Ist verständlich, wer die Tickets sehen darf und an wen du dich bei einer falschen oder unerwarteten Ausgabe wenden kannst?

## Projektrisiken und Gegenmaßnahmen

| Risiko | Maßnahme und Prüfpunkt |
|---|---|
| Chat- oder Embedding-Dienst fällt vor der Vorführung aus | Beide Dienste vor dem Modelllauf über `/api/status` prüfen. Den Ablauf mit fiktiven Daten zusätzlich im Mock-Modus vorführen können und den Betriebsmodus sichtbar benennen. |
| KI übersieht dringende Tickets oder schlägt einen unpassenden Lösungsweg vor | Die vier Qualitätsziele auf den festgelegten Prüffällen auswerten. Fehler mit Ticketnummer und Sollwert festhalten. Der Support kann die Priorität korrigieren und die vorgeschlagene Quelle öffnen. |
| Gleichzeitige Änderungen gehen verloren | Die synchronisierte Arbeitskopie mit einem Uvicorn-Worker betreiben. Die Regressionstests prüfen unter anderem, dass manuelle Änderungen erhalten bleiben und ein verspätetes KI-Ergebnis nach einem Reset verworfen wird. |
| Laufzeitdaten oder echte Zugangsdaten geraten in Git oder an unberechtigte Geräte | Vor dem Review geänderte und für den Commit vorgesehene Dateien prüfen. Für die Mac-Freigabe die Erreichbarkeit von einem zugelassenen Projektgerät und die Zugriffssperre außerhalb des freigegebenen Netzes kontrollieren. |
| Die Abgabe enthält nur Mock-Werte oder nicht zuordenbare Ergebnisse | Promptvergleich, Fallsuche und Doku-Suche auf der abgestimmten Modellkonfiguration ausführen. Modell, Betriebsmodus, Commit und Datum mit den Einzelberichten dokumentieren. |

Die Schritte für Messlauf und Vorführung stehen im [Prüf- und Demoablauf](test-und-demo.md).
