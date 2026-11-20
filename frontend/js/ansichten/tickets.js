// Ticketliste mit Filtern. Filter stehen in der Adresse (#/tickets?status=neu),
// damit die Kacheln der Übersicht direkt gefilterte Listen öffnen können.

import { PRIORITAET, STATUS } from "../config.js";
import {
  alter, h, istOffen, istSpamVerdacht, nachDringlichkeit, prioBadge, prioRang, sla, slaAmpel,
  statusBadge, ticketNr,
} from "../hilfen.js";
import { anzeigeName, kundeName, mitarbeiterListe, zustand } from "../zustand.js";

const SORTIERUNGEN = {
  dringlichkeit: { text: "Dringlichkeit", fn: nachDringlichkeit },
  neueste: { text: "Neueste zuerst", fn: (a, b) => b.id - a.id },
  aelteste: { text: "Älteste zuerst", fn: (a, b) => a.id - b.id },
  prioritaet: { text: "Priorität", fn: (a, b) => prioRang(b) - prioRang(a) || a.id - b.id },
};

export function zeigeTickets(ziel, { abfrage }) {
  const filter = {
    suche: abfrage.get("suche") || "",
    status: abfrage.get("status") || "offen",
    kunde: abfrage.get("kunde") || "",
    prioritaet: abfrage.get("prioritaet") || "",
    bearbeiter: abfrage.get("bearbeiter") || "",
    sla: abfrage.get("sla") || "",
    sortierung: SORTIERUNGEN[abfrage.get("sortierung")] ? abfrage.get("sortierung") : "dringlichkeit",
  };

  // Filter ändern = Adresse ändern, das zeichnet die Ansicht neu
  const setze = (name, wert) => {
    const neu = new URLSearchParams(abfrage);
    if (wert) neu.set(name, wert);
    else neu.delete(name);
    if (name === "status" && wert === "offen") neu.delete("status");
    location.hash = `#/tickets${neu.toString() ? `?${neu}` : ""}`;
  };

  const auswahl = (name, beschriftung, optionen) => {
    const el = h("select", { "aria-label": beschriftung },
      optionen.map(([wert, text]) => h("option", { value: wert, selected: filter[name] === wert }, text)));
    el.addEventListener("change", () => setze(name, el.value));
    return el;
  };

  const suche = h("input", {
    type: "search", value: filter.suche, placeholder: "Suche in Betreff, Text, Nummer …",
    "aria-label": "Tickets durchsuchen",
  });
  suche.addEventListener("change", () => setze("suche", suche.value.trim()));

  const leiste = h("div", { class: "filterleiste" },
    suche,
    auswahl("status", "Status", [
      ["offen", "Alle offenen"], ...Object.entries(STATUS), ["alle", "Alle inkl. geschlossen"],
    ]),
    auswahl("kunde", "Kunde", [["", "Alle Kunden"], ...zustand.kunden.map((k) => [k.kunde, k.name]), ["_ohne", "Unbekannter Absender"]]),
    auswahl("prioritaet", "Priorität", [["", "Alle Prioritäten"], ...Object.entries(PRIORITAET), ["_ohne", "Noch nicht bewertet"]]),
    auswahl("bearbeiter", "Bearbeiter", [
      ["", "Alle Bearbeiter"], ["_ohne", "Nicht zugewiesen"],
      ...mitarbeiterListe().map((m) => [m, anzeigeName(m)]),
    ]),
    auswahl("sortierung", "Sortierung", Object.entries(SORTIERUNGEN).map(([k, v]) => [k, v.text])),
  );

  const liste = filtern(zustand.tickets, filter).sort(SORTIERUNGEN[filter.sortierung].fn);
  const aktiveFilter = ["suche", "kunde", "prioritaet", "bearbeiter", "sla"].some((f) => filter[f])
    || filter.status !== "offen";

  ziel.append(
    h("section", { class: "karte" },
      leiste,
      h("div", { class: "liste-info" },
        h("span", {}, `${liste.length} ${liste.length === 1 ? "Ticket" : "Tickets"}`),
        filter.sla === "rot" ? h("span", { class: "badge" }, "nur SLA überschritten") : null,
        aktiveFilter ? h("a", { href: "#/tickets", class: "link" }, "Filter zurücksetzen") : null),
      liste.length ? ticketTabelle(liste) : h("p", { class: "leer" }, "Keine Tickets für diese Filter.")),
  );
}

function filtern(tickets, f) {
  const text = f.suche.toLowerCase().replace(/^#/, "");
  return tickets.filter((t) => {
    if (f.status === "offen" && !istOffen(t)) return false;
    if (f.status !== "offen" && f.status !== "alle" && t.status !== f.status) return false;
    if (f.kunde === "_ohne" ? t.kunde : f.kunde && t.kunde !== f.kunde) return false;
    if (f.prioritaet === "_ohne" ? t.prioritaet : f.prioritaet && t.prioritaet !== f.prioritaet) return false;
    if (f.bearbeiter === "_ohne" ? t.zugewiesen_an : f.bearbeiter && t.zugewiesen_an !== f.bearbeiter) return false;
    if (f.sla && sla(t).zustand !== f.sla) return false;
    if (text) {
      const inhalt = `${t.id} ${t.titel} ${t.beschreibung} ${kundeName(t.kunde)}`.toLowerCase();
      if (!inhalt.includes(text)) return false;
    }
    return true;
  });
}

// Tabelle, die auch die Übersicht verwendet. Ganze Zeile ist klickbar.
export function ticketTabelle(tickets, { kompakt = false } = {}) {
  const kopf = ["SLA", "Nr.", "Betreff und Kunde", "Status", "Priorität", kompakt ? null : "Bearbeiter", "Erstellt"]
    .filter(Boolean);

  return h("div", { class: "tabelle-huelle" },
    h("table", { class: "tabelle" },
      h("thead", {}, h("tr", {}, kopf.map((k) => h("th", { scope: "col" }, k)))),
      h("tbody", {}, tickets.map((t) => {
        const zeile = h("tr", { class: istSpamVerdacht(t) ? "zeile-spam" : "" },
          h("td", { class: "spalte-sla" }, slaAmpel(t)),
          h("td", { class: "nr" }, h("a", { href: `#/ticket/${t.id}` }, ticketNr(t.id))),
          h("td", { class: "betreff", title: t.titel },
            h("span", { class: "betreff-titel" }, t.titel,
              istSpamVerdacht(t) ? h("span", { class: "badge badge-ki" }, "Spam?") : null),
            h("span", { class: "betreff-kunde" }, kundeName(t.kunde))),
          h("td", {}, statusBadge(t.status)),
          h("td", {}, prioBadge(t.prioritaet, t.prioritaet_quelle)),
          kompakt ? null : h("td", {}, t.zugewiesen_an ? anzeigeName(t.zugewiesen_an) : h("span", { class: "gedimmt" }, "–")),
          h("td", { class: "gedimmt", title: t.erstellt_am }, alter(t.erstellt_am)));
        zeile.addEventListener("click", (ev) => {
          if (ev.target.closest("a")) return;
          location.hash = `#/ticket/${t.id}`;
        });
        return zeile;
      }))));
}
