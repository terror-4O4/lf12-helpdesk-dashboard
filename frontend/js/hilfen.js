// Kleine Hilfsfunktionen: Elemente bauen, Zeiten, SLA, Markdown, Badges.
//
// Wichtig: Inhalte aus Tickets werden IMMER als Text eingefügt (textContent),
// nie als HTML. So kann eine Mail mit <script> o. Ä. im Dashboard nichts
// ausführen. Deshalb gibt es hier keinen innerHTML-Aufruf.

import {
  DEMO_JETZT, PRIORITAET, PRIO_RANG, SLA_GELB_AB, SLA_LAEUFT_BEI, SLA_MINUTEN, STATUS,
} from "./config.js";

// --- Elemente bauen -------------------------------------------------------
// h("button", { class: "knopf", onclick: fn }, "Text", kindElement)
export function h(tag, attribute = {}, ...kinder) {
  const el = document.createElement(tag);
  for (const [name, wert] of Object.entries(attribute || {})) {
    if (wert === null || wert === undefined || wert === false) continue;
    if (name.startsWith("on") && typeof wert === "function") {
      el.addEventListener(name.slice(2), wert);
    } else if (name === "class") {
      el.className = wert;
    } else if (name === "value") {
      el.value = wert;
    } else if (wert === true) {
      el.setAttribute(name, "");
    } else {
      el.setAttribute(name, String(wert));
    }
  }
  anhaengen(el, kinder);
  return el;
}

// Wie el.append(), überspringt aber null/false (für "bedingung ? element : null")
export function fuege(el, ...kinder) {
  anhaengen(el, kinder);
}

function anhaengen(el, kinder) {
  for (const kind of kinder.flat(Infinity)) {
    if (kind === null || kind === undefined || kind === false) continue;
    el.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
  }
}

export function leeren(el) {
  while (el.firstChild) el.firstChild.remove();
}

// --- Zeit -----------------------------------------------------------------
// Zeitstempel ohne Zeitzone ("2026-11-19T08:12:00") liest der Browser als Ortszeit.
export function zeit(text) {
  const datum = text ? new Date(text) : null;
  return datum && !Number.isNaN(datum.getTime()) ? datum : null;
}

function festeZeit() {
  const ausAdresse = new URLSearchParams(location.search).get("jetzt");
  return zeit(ausAdresse) || zeit(DEMO_JETZT);
}

export function jetzt() {
  return festeZeit() || new Date();
}

export function istDemoZeit() {
  return Boolean(festeZeit());
}

const DATUM = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" });
const UHR = new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" });

export function formatZeit(text) {
  const d = zeit(text);
  if (!d) return "";
  return `${DATUM.format(d)} ${UHR.format(d)}`; // "19.11. 08:12"
}

export function dauer(minuten) {
  const m = Math.round(Math.abs(minuten));
  if (m < 60) return `${m} Min.`;
  // Minuten nur bei kurzen Zeiten, sonst wird es unübersichtlich
  if (m < 180) return `${Math.floor(m / 60)} Std.${m % 60 ? ` ${m % 60} Min.` : ""}`;
  if (m < 60 * 24) return `${Math.round(m / 60)} Std.`;
  const tage = Math.floor(m / 1440);
  return `${tage} ${tage === 1 ? "Tag" : "Tage"}`;
}

export function alter(text, bezugszeit = jetzt()) {
  const d = zeit(text);
  if (!d) return "";
  const min = (bezugszeit - d) / 60000;
  return min < 1 ? "gerade eben" : `vor ${dauer(min)}`;
}

// --- Ticket-Logik ---------------------------------------------------------
export const istOffen = (t) => t.status !== "geschlossen";

export const istImSpamfilter = (t) =>
  t.spam_entscheidung === "spam" || (!t.spam_entscheidung && t.ki?.spam === true);

export const spamOffen = (t) => istOffen(t) && !t.spam_entscheidung && istImSpamfilter(t);

export function spamBadge(t) {
  if (t.spam_entscheidung === "spam") return h("span", { class: "badge" }, "Spam bestätigt");
  if (istImSpamfilter(t)) {
    return t.ki.modus === "mock" ? h("span", { class: "badge" }, "Demo-Spamverdacht")
      : h("span", { class: "badge badge-ki" }, "✦ Spam-Verdacht");
  }
  return null;
}

export const prioRang = (t) => PRIO_RANG[t.prioritaet] || 0;

export const hatHandlungsbedarf = (t) =>
  SLA_LAEUFT_BEI.includes(t.status) && !istImSpamfilter(t);

// Seit wann ist das Ticket im aktuellen Status?
function seitStatus(t) {
  const liste = t.statushistorie || [];
  const letzter = liste[liste.length - 1];
  return zeit(letzter?.seit) || zeit(t.erstellt_am);
}

export function wartezeit(t, bezugszeit = jetzt()) {
  const wartetAufKunde = t.status === "warten_auf_kunde";
  if ((!wartetAufKunde && !SLA_LAEUFT_BEI.includes(t.status)) || istImSpamfilter(t)) return null;
  const seit = seitStatus(t);
  if (!seit) return null;
  return {
    auf: wartetAufKunde ? "Kunde" : "Support",
    minuten: Math.max(0, (bezugszeit - seit) / 60000),
  };
}

// Ergebnis: { zustand: "gruen" | "gelb" | "rot" | "pausiert" | "keine", anteil, text }
export function sla(t, bezugszeit = jetzt()) {
  if (!istOffen(t) || istImSpamfilter(t)) return { zustand: "keine", anteil: -1, text: "" };
  if (!SLA_LAEUFT_BEI.includes(t.status)) {
    return { zustand: "pausiert", anteil: -1, text: "SLA pausiert" };
  }
  const warten = wartezeit(t, bezugszeit);
  if (!warten) return { zustand: "keine", anteil: -1, text: "" };
  const grenze = SLA_MINUTEN[t.prioritaet] ?? SLA_MINUTEN.unbewertet;
  const vergangen = warten.minuten;
  const anteil = vergangen / grenze;
  const rest = grenze - vergangen;
  if (rest === 0) return { zustand: "rot", anteil, text: "Reaktionsfrist erreicht" };
  if (anteil >= 1) return { zustand: "rot", anteil, text: `${dauer(rest)} überschritten` };
  return {
    zustand: anteil >= SLA_GELB_AB ? "gelb" : "gruen",
    anteil,
    text: `noch ${dauer(rest)}`,
  };
}

// Sortierung "was ist am dringendsten": SLA-Verbrauch, dann Priorität, dann Alter
export function nachDringlichkeit(a, b, bezugszeit = jetzt()) {
  return Number(hatHandlungsbedarf(b)) - Number(hatHandlungsbedarf(a))
    || sla(b, bezugszeit).anteil - sla(a, bezugszeit).anteil
    || prioRang(b) - prioRang(a)
    || (zeit(a.erstellt_am)?.getTime() ?? Infinity) - (zeit(b.erstellt_am)?.getTime() ?? Infinity)
    || a.id - b.id;
}

// --- Badges ---------------------------------------------------------------
export function statusBadge(status) {
  return h("span", { class: `badge status-${status}` }, STATUS[status] || status);
}

export function ticketPrioBadge(t) {
  const quelle = t.prioritaet_quelle === "ki" && t.ki?.modus === "mock" ? "mock" : t.prioritaet_quelle;
  return prioBadge(t.prioritaet, quelle);
}

export function prioBadge(prio, quelle) {
  if (!prio) return h("span", { class: "badge prio-leer", title: "Noch nicht bewertet" }, "offen");
  const herkunft = { ki: "Vom lokalen Sprachmodell vorgeschlagene Priorität", mock: "Demo-Bewertung ohne Sprachmodell",
    manuell: "Von Hand gesetzt" };
  return h(
    "span",
    { class: `badge prio-${prio}`, title: herkunft[quelle] || "Herkunft der Priorität unbekannt" },
    PRIORITAET[prio] || prio,
    quelle === "ki" ? h("span", { class: "ki-zeichen", role: "img", "aria-label": "KI-Vorschlag" }, " ✦") : null,
  );
}

export function slaAmpel(t, mitText = false, bezugszeit = jetzt()) {
  const s = sla(t, bezugszeit);
  if (s.zustand === "keine") return h("span", { class: "ampel ampel-keine", "aria-hidden": "true" });
  return h(
    "span",
    { class: `ampel-wrap`, title: s.text },
    h("span", { class: `ampel ampel-${s.zustand}`, role: "img", "aria-label": `SLA: ${s.text}` }),
    mitText ? h("span", { class: "ampel-text" }, s.text) : null,
  );
}

// Einheitliche Kennzeichnung für alles, was von der KI stammt
export function kiMarke(text = "KI") {
  return h("span", { class: "ki-marke" }, "✦ ", text);
}

export const ticketNr = (id) => `#${id}`;

export function dokuQuellen(quellen, antwort = "") {
  if (!quellen?.length) return null;
  return h("ul", { class: "doku-quellen", "aria-label": "Quellen" },
    quellen.map(({ titel, quelle, text, links, ticket_id }) => h("li", {},
      Number.isSafeInteger(ticket_id)
        ? h("a", { href: `#/ticket/${ticket_id}` }, `#${ticket_id} ${titel}`)
        : h("strong", {}, titel),
      h("div", { class: "klein gedimmt" }, "Fundstelle ", quelle),
      text === antwort ? null : h("div", { class: "md" }, markdown(text)),
      h("div", { class: "doku-links" }, links?.map(dokuLink)))));
}

function dokuLink(link) {
  try {
    const url = new URL(link.url);
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) return null;
    return h("a", { href: url.href, target: "_blank", rel: "noopener noreferrer" }, link.titel);
  } catch {
    return null;
  }
}

// --- Markdown (klein, nur das Nötigste) -----------------------------------
// Unterstützt: # Überschriften, - Listen, 1. Listen, **fett**, `Code`, Absätze.
export function markdown(text) {
  const wurzel = document.createDocumentFragment();
  let liste = null;
  let absatz = [];

  const absatzEnde = () => {
    if (absatz.length) wurzel.append(h("p", {}, inline(absatz.join(" "))));
    absatz = [];
  };
  const listeEnde = () => {
    liste = null;
  };

  for (const roh of String(text || "").split("\n")) {
    const zeile = roh.trimEnd();
    const ueberschrift = zeile.match(/^(#{1,4})\s+(.*)$/);
    const punkt = zeile.match(/^\s*[-*•]\s+(.*)$/);
    const nummer = zeile.match(/^\s*\d+[.)]\s+(.*)$/);

    if (!zeile.trim()) {
      absatzEnde();
      listeEnde();
    } else if (ueberschrift) {
      absatzEnde();
      listeEnde();
      const ebene = Math.min(ueberschrift[1].length + 2, 6);
      wurzel.append(h(`h${ebene}`, { class: "md-titel" }, inline(ueberschrift[2])));
    } else if (punkt || nummer) {
      absatzEnde();
      const art = punkt ? "ul" : "ol";
      if (!liste || liste.tagName.toLowerCase() !== art) {
        liste = h(art);
        wurzel.append(liste);
      }
      liste.append(h("li", {}, inline((punkt || nummer)[1])));
    } else {
      listeEnde();
      absatz.push(zeile.trim());
    }
  }
  absatzEnde();
  return wurzel;
}

function inline(text) {
  const teile = [];
  const muster = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let pos = 0;
  for (const treffer of text.matchAll(muster)) {
    teile.push(text.slice(pos, treffer.index));
    const t = treffer[0];
    teile.push(t.startsWith("**") ? h("strong", {}, t.slice(2, -2)) : h("code", {}, t.slice(1, -1)));
    pos = treffer.index + t.length;
  }
  teile.push(text.slice(pos));
  return teile;
}
