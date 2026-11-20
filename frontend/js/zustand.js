// Gemeinsamer Zustand aller Ansichten: geladene Daten, gewählter Mitarbeiter,
// Meldungen (Toasts). Die Ansichten lesen von hier und rufen neuZeichnen()
// auf, wenn sich etwas geändert hat.

import { api } from "./api.js";
import { h } from "./hilfen.js";

export const zustand = {
  tickets: [],
  kunden: [],
  kiStatus: null,
  mitarbeiter: lokalLesen("mitarbeiter", ""),
};

export async function ladeDaten() {
  const [tickets, kunden] = await Promise.all([api.tickets(), api.kunden()]);
  zustand.tickets = tickets;
  zustand.kunden = kunden;
}

// Ersetzt ein Ticket in der Liste, ohne alles neu zu laden
export function ticketErsetzen(neu) {
  const i = zustand.tickets.findIndex((t) => t.id === neu.id);
  if (i >= 0) zustand.tickets[i] = neu;
  else zustand.tickets.push(neu);
}

export function kundeName(kuerzel) {
  if (!kuerzel) return "Unbekannter Absender";
  return zustand.kunden.find((k) => k.kunde === kuerzel)?.name || kuerzel;
}

// Solange es kein eigenes Mitarbeiter-Format gibt: Kürzel aus den Tickets
export function mitarbeiterListe() {
  const namen = new Set(zustand.tickets.map((t) => t.zugewiesen_an).filter(Boolean));
  if (zustand.mitarbeiter) namen.add(zustand.mitarbeiter);
  return [...namen].sort();
}

export function mitarbeiterSetzen(kuerzel) {
  zustand.mitarbeiter = kuerzel;
  lokalSchreiben("mitarbeiter", kuerzel);
}

export const anzeigeName = (kuerzel) =>
  kuerzel ? kuerzel.charAt(0).toUpperCase() + kuerzel.slice(1) : "niemand";

// --- Neu zeichnen ---------------------------------------------------------
let zeichner = () => {};
export function setzeZeichner(fn) {
  zeichner = fn;
}
export function neuZeichnen() {
  zeichner();
}

// --- Browser-Speicher -----------------------------------------------------
// Nur für Bequemlichkeit (Mitarbeiter, To-dos). Kann leer oder gesperrt sein,
// daher immer mit try/catch.
export function lokalLesen(schluessel, standard) {
  try {
    const wert = localStorage.getItem(`lf12.${schluessel}`);
    return wert === null ? standard : JSON.parse(wert);
  } catch {
    return standard;
  }
}

export function lokalSchreiben(schluessel, wert) {
  try {
    localStorage.setItem(`lf12.${schluessel}`, JSON.stringify(wert));
  } catch {
    // Speicher nicht verfügbar: dann eben nur bis zum Neuladen
  }
}

// --- Meldungen ------------------------------------------------------------
export function meldung(text, art = "info", aktion = null) {
  const bereich = document.getElementById("meldungen");
  const el = h(
    "div",
    { class: `meldung meldung-${art}`, role: art === "fehler" ? "alert" : "status" },
    h("span", {}, text),
    aktion ? h("a", { href: aktion.href, class: "meldung-link" }, aktion.text) : null,
    h("button", { class: "meldung-zu", "aria-label": "Schließen", onclick: () => el.remove() }, "×"),
  );
  bereich.append(el);
  setTimeout(() => el.remove(), art === "fehler" ? 9000 : 5000);
}
