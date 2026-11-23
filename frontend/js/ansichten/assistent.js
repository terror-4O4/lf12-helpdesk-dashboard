// KI-Assistent: Seitenleiste rechts, von überall aufrufbar. Optional mit einem
// Ticket als Kontext. Der Verlauf bleibt nur bis zum Neuladen der Seite.

import { api } from "../api.js";
import { MAX_FRAGE } from "../config.js";
import { dokuQuellen, h, kiMarke, leeren, markdown, ticketNr } from "../hilfen.js";
import { kundeName, zustand } from "../zustand.js";

const VORSCHLAEGE = [
  "Outlook startet nicht. Was kann ich prüfen?",
  "Wie leere ich die Druckwarteschlange auf einem Windows-Server?",
  "Woran erkenne ich eine Phishing-Mail?",
];

const verlaeufe = new Map();
const entwuerfe = new Map();
let kontext = null; // Ticket oder null
const wartend = new Set();

let panel, liste, eingabe, kontextZeile, kundenAuswahl, senden;

export function initAssistent() {
  panel = document.getElementById("assistent");
  liste = h("div", { class: "chat", role: "log", "aria-live": "polite" });
  kontextZeile = h("div", { class: "kontext" });
  kundenAuswahl = h("select", { id: "assistent-kunde", onchange: bereichAnzeigen },
    h("option", { value: "" }, "Allgemeine KI-Frage"));
  eingabe = h("textarea", {
    rows: 3, maxlength: MAX_FRAGE,
    "aria-label": "Frage an die KI",
  });
  eingabe.addEventListener("input", () => entwuerfe.set(kundenAuswahl.value, eingabe.value));
  senden = h("button", { class: "knopf knopf-ki", type: "submit" }, "Senden");

  const formular = h("form", { class: "chat-eingabe" },
    h("label", { for: "assistent-kunde" }, "Suchbereich", kundenAuswahl), eingabe, senden);
  formular.addEventListener("submit", (ev) => {
    ev.preventDefault();
    fragen(eingabe.value);
  });
  eingabe.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      fragen(eingabe.value);
    }
  });

  panel.append(
    h("div", { class: "assistent-kopf" },
      h("h2", {}, kiMarke("KI-Assistent")),
      h("button", { class: "knopf-klein", "aria-label": "KI-Assistent schließen", onclick: schliessen }, "×")),
    kontextZeile, liste, formular,
    h("p", { class: "klein gedimmt assistent-fuss" },
      "Antworten der KI können falsch sein. Die Anfrage geht nur an den lokalen KI-Server."));

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !panel.hidden && !document.querySelector("dialog[open]")) schliessen();
  });
  window.addEventListener("hashchange", () => {
    if (!panel.hidden && kontext && location.hash.split("?")[0] !== `#/ticket/${kontext.id}`) schliessen();
  });
  zeichne();
}

export function oeffneAssistent(ticket = null, bereich = "ticket") {
  kontext = ticket;
  kundenAuswahl.replaceChildren(
    ...(ticket ? [h("option", { value: `ticket:${ticket.id}` }, `Hilfe zu Ticket ${ticketNr(ticket.id)}`)] : []),
    h("option", { value: "" }, "Allgemeine KI-Frage"),
    h("option", { value: "wiki" }, "Wikipedia · IT-Grundwissen"),
    ...zustand.kunden.map((kunde) => h("option", { value: `doku:${kunde.kunde}` }, `Kundendoku · ${kunde.name}`)));
  kundenAuswahl.value = ticket ? (bereich === "doku" && ticket.kunde ? `doku:${ticket.kunde}` : `ticket:${ticket.id}`) : "";
  panel.hidden = false;
  document.body.classList.add("assistent-offen");
  bereichAnzeigen();
  eingabe.focus();
}

function bereichAnzeigen() {
  eingabe.value = entwuerfe.get(kundenAuswahl.value) || "";
  zeichne();
}

function schliessen() {
  panel.hidden = true;
  document.body.classList.remove("assistent-offen");
  document.getElementById("assistent-oeffnen").focus();
}

function zeichne() {
  const bereich = kundenAuswahl.value;
  const istTicket = bereich.startsWith("ticket:");
  const istWiki = bereich === "wiki";
  const dokuKunde = bereich.startsWith("doku:") ? bereich.slice(5) : "";
  const verlauf = verlaeufe.get(bereich) || [];
  senden.disabled = wartend.has(bereich);
  eingabe.placeholder = istTicket ? "Frage zu diesem Ticket …" : istWiki ? "IT-Begriff eingeben …" : dokuKunde
    ? "Frage zur ausgewählten Kundendoku …"
    : "Frage an die KI … (Enter = senden, Umschalt+Enter = neue Zeile)";
  leeren(kontextZeile);
  if (istTicket && kontext) {
    kontextZeile.append(h("span", {}, `${ticketNr(kontext.id)} ${kontext.titel}`));
  }
  kontextZeile.hidden = !istTicket;

  leeren(liste);
  if (!verlauf.length) {
    const einstieg = dokuKunde ? `Frag etwas zur Kundendoku von ${kundeName(dokuKunde)}.`
      : istTicket ? "Wobei brauchst du Hilfe?"
        : istWiki ? "Welchen IT-Begriff möchtest du nachschlagen?"
        : "Frag nach Lösungswegen. Zum Beispiel:";
    liste.append(h("div", { class: "chat-leer" },
      h("p", {}, einstieg),
      dokuKunde || istWiki ? null : h("div", { class: "vorschlaege" },
        (istTicket ? ["Was ist der nächste Schritt?", "Gibt es einen ähnlichen gelösten Fall?"] : VORSCHLAEGE)
          .map((v) => h("button", { class: "knopf-chip", type: "button", onclick: () => fragen(v) }, v)))));
  }
  for (const n of verlauf) {
    liste.append(h("div", { class: `blase blase-${n.rolle}` },
      n.rolle === "ki" ? h("div", { class: "md" }, markdown(n.text)) : h("p", {}, n.text),
      n.quellen?.length ? h("details", { class: "chat-quellen" },
        h("summary", {}, n.quellen.length === 1 ? "1 Quelle" : `${n.quellen.length} Quellen`),
        dokuQuellen(n.quellen, n.text)) : null,
      n.info ? h("span", { class: "blase-info" }, n.info) : null));
  }
  if (wartend.has(bereich)) {
    liste.append(h("div", { class: "blase blase-ki blase-wartet" }, h("span", { class: "punkte" }, "KI denkt nach"), h("span", { class: "sekunden" })));
  }
  const letzte = liste.lastElementChild;
  if (letzte) liste.scrollTop += letzte.getBoundingClientRect().top - liste.getBoundingClientRect().top - 8;
}

async function fragen(text) {
  const frage = text.trim();
  const bereich = kundenAuswahl.value;
  if (!frage || wartend.has(bereich)) return;
  if (!verlaeufe.has(bereich)) verlaeufe.set(bereich, []);
  const verlauf = verlaeufe.get(bereich);
  const vorherige = verlauf.findLast(n => n.rolle === "ich")?.text;
  eingabe.value = "";
  entwuerfe.delete(bereich);
  verlauf.push({ rolle: "ich", text: frage });
  wartend.add(bereich);
  zeichne();

  const start = Date.now();
  const uhr = setInterval(() => {
    const el = liste.querySelector(".sekunden");
    if (el && kundenAuswahl.value === bereich) el.textContent = ` ${Math.round((Date.now() - start) / 1000)} s`;
  }, 500);

  try {
    let r;
    if (bereich.startsWith("ticket:")) r = await api.frageTicket(Number(bereich.slice(7)), frage, vorherige);
    else if (bereich.startsWith("doku:")) r = await api.frageKundendoku(bereich.slice(5), frage);
    else if (bereich === "wiki") r = await api.frageWikipedia(frage);
    else r = await api.frage(frage);
    const info = r.modus === "mock" ? "Demo-Modus" : "";
    verlauf.push({ rolle: "ki", text: r.antwort, info, quellen: r.quellen });
  } catch (e) {
    verlauf.push({ rolle: "ki", text: `Fehler: ${e.message}`, info: "" });
  } finally {
    clearInterval(uhr);
    wartend.delete(bereich);
    zeichne();
    if (!panel.hidden && kundenAuswahl.value === bereich) eingabe.focus();
  }
}
