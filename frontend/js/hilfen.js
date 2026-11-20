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
  return text ? new Date(text) : null;
}

export function jetzt() {
  const ausAdresse = new URLSearchParams(location.search).get("jetzt");
  const fest = ausAdresse || DEMO_JETZT;
  if (fest) {
    const d = new Date(fest);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return new Date();
}

export function istDemoZeit() {
  return Boolean(new URLSearchParams(location.search).get("jetzt") || DEMO_JETZT);
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

export function alter(text) {
  const d = zeit(text);
  if (!d) return "";
  const min = (jetzt() - d) / 60000;
  return min < 1 ? "gerade eben" : `vor ${dauer(min)}`;
}

// --- Ticket-Logik ---------------------------------------------------------
export const istOffen = (t) => t.status !== "geschlossen";

// Spam-Verdacht: KI sagt Spam und kein Mitarbeiter hat widersprochen
export const istSpamVerdacht = (t) =>
  Boolean(t.ki?.spam) && t.spam_entscheidung !== "kein_spam" && istOffen(t);

// Noch zu entscheiden auf der Spam-Seite
export const spamOffen = (t) => istSpamVerdacht(t) && !t.spam_entscheidung;

export const prioRang = (t) => PRIO_RANG[t.prioritaet] || 0;

// Seit wann ist das Ticket im aktuellen Status?
function seitStatus(t) {
  const liste = t.statushistorie || [];
  const letzter = liste[liste.length - 1];
  return zeit(letzter?.seit || t.erstellt_am);
}

// Ergebnis: { zustand: "gruen" | "gelb" | "rot" | "pausiert" | "keine", anteil, text }
export function sla(t) {
  if (!istOffen(t) || istSpamVerdacht(t)) return { zustand: "keine", anteil: -1, text: "" };
  if (!SLA_LAEUFT_BEI.includes(t.status)) {
    return { zustand: "pausiert", anteil: -1, text: "SLA pausiert" };
  }
  const grenze = SLA_MINUTEN[t.prioritaet] ?? SLA_MINUTEN.unbewertet;
  const vergangen = (jetzt() - seitStatus(t)) / 60000;
  const anteil = vergangen / grenze;
  const rest = grenze - vergangen;
  if (anteil >= 1) return { zustand: "rot", anteil, text: `${dauer(rest)} überschritten` };
  return {
    zustand: anteil >= SLA_GELB_AB ? "gelb" : "gruen",
    anteil,
    text: `noch ${dauer(rest)}`,
  };
}

// Sortierung "was ist am dringendsten": SLA-Verbrauch, dann Priorität, dann Alter
export function nachDringlichkeit(a, b) {
  return sla(b).anteil - sla(a).anteil || prioRang(b) - prioRang(a) || a.id - b.id;
}

// --- Badges ---------------------------------------------------------------
export function statusBadge(status) {
  return h("span", { class: `badge status-${status}` }, STATUS[status] || status);
}

export function prioBadge(prio, quelle) {
  if (!prio) return h("span", { class: "badge prio-leer", title: "Noch nicht bewertet" }, "offen");
  const ki = quelle === "ki";
  return h(
    "span",
    { class: `badge prio-${prio}`, title: ki ? "Von der KI gesetzt" : "Von Hand gesetzt" },
    PRIORITAET[prio] || prio,
    ki ? h("span", { class: "ki-zeichen", "aria-label": "KI" }, " ✦") : null,
  );
}

export function slaAmpel(t, mitText = false) {
  const s = sla(t);
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
