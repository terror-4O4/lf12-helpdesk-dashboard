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

const verlauf = []; // { rolle: "ich" | "ki", text, info, quellen }
let kontext = null; // Ticket oder null
let wartet = false;

let panel, liste, eingabe, kontextZeile, kundenAuswahl, senden;

export function initAssistent() {
  panel = document.getElementById("assistent");
  liste = h("div", { class: "chat", role: "log", "aria-live": "polite" });
  kontextZeile = h("div", { class: "kontext" });
  kundenAuswahl = h("select", { id: "assistent-kunde", onchange: zeichne },
    h("option", { value: "" }, "Allgemeine KI-Frage"));
  eingabe = h("textarea", {
    rows: 3, maxlength: MAX_FRAGE,
    "aria-label": "Frage an die KI",
  });
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
  zeichne();
}

export function oeffneAssistent(ticket = null) {
  kontext = ticket;
  kundenAuswahl.replaceChildren(
    h("option", { value: "" }, "Allgemeine KI-Frage"),
    ...zustand.kunden.map((kunde) => h("option", { value: kunde.kunde }, `Kundendoku · ${kunde.name}`)));
  kundenAuswahl.value = zustand.kunden.some((kunde) => kunde.kunde === ticket?.kunde) ? ticket.kunde : "";
  panel.hidden = false;
  document.body.classList.add("assistent-offen");
  zeichne();
  eingabe.focus();
}

function schliessen() {
  panel.hidden = true;
  document.body.classList.remove("assistent-offen");
  document.getElementById("assistent-oeffnen").focus();
}

function zeichne() {
  const dokuKunde = kundenAuswahl.value;
  eingabe.placeholder = dokuKunde
    ? "Frage zur ausgewählten Kundendoku …"
    : "Frage an die KI … (Enter = senden, Umschalt+Enter = neue Zeile)";
  leeren(kontextZeile);
  if (kontext && !dokuKunde) {
    kontextZeile.append(
      h("span", {}, `Kontext: ${ticketNr(kontext.id)} ${kontext.titel}`),
      h("button", {
        class: "knopf-klein", "aria-label": "Kontext entfernen",
        onclick: () => { kontext = null; zeichne(); },
      }, "×"));
  }
  kontextZeile.hidden = !kontext || Boolean(dokuKunde);

  leeren(liste);
  if (!verlauf.length) {
    const einstieg = dokuKunde ? `Frag etwas zur Kundendoku von ${kundeName(dokuKunde)}.`
      : kontext ? "Frag etwas zu diesem Ticket, z. B. nach möglichen Ursachen."
        : "Frag nach Lösungswegen. Zum Beispiel:";
    liste.append(h("div", { class: "chat-leer" },
      h("p", {}, einstieg),
      kontext || dokuKunde ? null : h("div", { class: "vorschlaege" },
        VORSCHLAEGE.map((v) => h("button", { class: "knopf-chip", type: "button", onclick: () => fragen(v) }, v)))));
  }
  for (const n of verlauf) {
    liste.append(h("div", { class: `blase blase-${n.rolle}` },
      n.rolle === "ki" ? h("div", { class: "md" }, markdown(n.text)) : h("p", {}, n.text),
      dokuQuellen(n.quellen, n.text),
      n.info ? h("span", { class: "blase-info" }, n.info) : null));
  }
  if (wartet) {
    liste.append(h("div", { class: "blase blase-ki blase-wartet" }, h("span", { class: "punkte" }, "KI denkt nach"), h("span", { class: "sekunden" })));
  }
  liste.scrollTop = liste.scrollHeight;
}

// Ticket als Kontext vor die Frage setzen, Gesamtlänge begrenzen (Backend: 2000 Zeichen)
function mitKontext(frage) {
  if (!kontext) return frage;
  const kopf = `Zum Ticket ${ticketNr(kontext.id)} (Kunde: ${kundeName(kontext.kunde)})\nBetreff: ${kontext.titel}\nBeschreibung: `;
  const rest = `\n\nFrage: ${frage}`;
  const platz = MAX_FRAGE - kopf.length - rest.length;
  const beschreibung = kontext.beschreibung.length > platz
    ? `${kontext.beschreibung.slice(0, Math.max(0, platz - 1))}…`
    : kontext.beschreibung;
  return (kopf + beschreibung + rest).slice(0, MAX_FRAGE);
}

async function fragen(text) {
  const frage = text.trim();
  if (!frage || wartet) return;
  const dokuKunde = kundenAuswahl.value;
  eingabe.value = "";
  verlauf.push({ rolle: "ich", text: frage, info: dokuKunde ? `Kundendoku · ${kundeName(dokuKunde)}` : "" });
  wartet = true;
  senden.disabled = true;
  zeichne();

  const start = Date.now();
  const uhr = setInterval(() => {
    const el = liste.querySelector(".sekunden");
    if (el) el.textContent = ` ${Math.round((Date.now() - start) / 1000)} s`;
  }, 500);

  try {
    const r = await (dokuKunde ? api.frageKundendoku(dokuKunde, frage) : api.frage(mitKontext(frage)));
    const info = `${(r.dauer_ms / 1000).toFixed(1)} s${r.tokens ? ` · ${r.tokens} Tokens` : ""}${r.modus === "mock" ? " · Mock" : ""}`;
    verlauf.push({ rolle: "ki", text: r.antwort, info, quellen: r.quellen });
  } catch (e) {
    verlauf.push({ rolle: "ki", text: `Fehler: ${e.message}`, info: "" });
  } finally {
    clearInterval(uhr);
    wartet = false;
    senden.disabled = false;
    zeichne();
    eingabe.focus();
  }
}
