// Einstellungen des Dashboards an einer Stelle.
// Wer hier etwas ändert, sollte es auch in frontend/README.md nachziehen.

// --- SLA ------------------------------------------------------------------
// Reaktionszeit in Minuten je Priorität. Die SLA läuft, solange ein Ticket
// auf eine Reaktion von uns wartet (Status in SLA_LAEUFT_BEI). Gemessen wird
// ab dem letzten Statuswechsel.
export const SLA_MINUTEN = {
  sehr_hoch: 30,
  hoch: 120,
  mittel: 480,
  niedrig: 1440,
  unbewertet: 120, // noch keine Priorität: lieber zu früh als zu spät schauen
};
export const SLA_LAEUFT_BEI = ["neu", "antwort_erhalten"];
// Ab diesem Anteil der Zeit wird die Ampel gelb (0.5 = Hälfte verbraucht)
export const SLA_GELB_AB = 0.5;

// Feste "Jetzt"-Zeit für Demos, z. B. "2026-11-19T11:30:00".
// null = echte Uhrzeit. Alternativ per Adresse: /?jetzt=2026-11-19T11:30
// Hintergrund: Die Testdaten haben feste Zeitstempel und wären sonst alle rot.
export const DEMO_JETZT = null;

// --- Anzeige-Texte --------------------------------------------------------
export const STATUS = {
  neu: "Neu",
  in_bearbeitung: "In Bearbeitung",
  warten_auf_kunde: "Warten auf Kunde",
  antwort_erhalten: "Antwort erhalten",
  geparkt: "Geparkt",
  geschlossen: "Geschlossen",
};

export const PRIORITAET = {
  sehr_hoch: "Sehr dringend",
  hoch: "Hoch",
  mittel: "Normal",
  niedrig: "Niedrig",
};

// Für die Sortierung: höher = wichtiger
export const PRIO_RANG = { sehr_hoch: 4, hoch: 3, mittel: 2, niedrig: 1 };

// --- Sonstiges ------------------------------------------------------------
// Wie oft der KI-Status oben rechts aktualisiert wird
export const STATUS_ABFRAGE_MS = 30000;
// Maximale Länge einer Frage an /api/ki/frage (Grenze im Backend)
export const MAX_FRAGE = 2000;
