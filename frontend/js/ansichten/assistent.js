// KI-Assistent: Seitenleiste rechts, von überall aufrufbar. Optional mit einem
// Ticket als Kontext. Der Verlauf bleibt nur bis zum Neuladen der Seite.

import { api } from "../api.js";
import { MAX_FRAGE } from "../config.js";
import { dokuQuellen, h, kiMarke, markdown, ticketNr } from "../hilfen.js";

const VORSCHLAEGE = [
  "Outlook startet nicht. Was kann ich prüfen?",
  "Wie leere ich die Druckwarteschlange auf einem Windows-Server?",
  "Woran erkenne ich eine Phishing-Mail?",
];

const ANTWORTHERKUNFT = {
  mock: "Demo-Modus",
  fachdialog: "Prüfanleitung aus dem Fachwissen",
  fachnotiz: "Prüfanleitung aus dem Fachwissen",
  modellvorschlag: "Prüfschritt vom lokalen Modell",
  modellrueckfrage: "Rückfrage vom lokalen Modell",
  standardpruefung: "Allgemeine Prüfhilfe",
};

const verlaeufe = new Map();
const entwuerfe = new Map();
let kontext = null; // Ticket oder null
const wartend = new Set();

let panel, liste, eingabe, kontextZeile, senden;

export function initAssistent() {
  panel = document.getElementById("assistent");
  liste = h("div", { class: "chat", role: "log", "aria-live": "polite" });
  kontextZeile = h("div", { class: "kontext" });
  eingabe = h("textarea", {
    rows: 3, maxlength: MAX_FRAGE,
    "aria-label": "Frage an die KI",
  });
  eingabe.addEventListener("input", () => entwuerfe.set(kontext?.id, eingabe.value));
  senden = h("button", { class: "knopf knopf-ki", type: "submit" }, "Senden");

  const formular = h("form", { class: "chat-eingabe" }, eingabe, senden);
  formular.addEventListener("submit", (ev) => {
    ev.preventDefault();
    fragen(eingabe.value);
  });
  eingabe.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
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

export function oeffneAssistent(ticket = null, vorgeschlageneFrage = "") {
  kontext = ticket;
  panel.hidden = false;
  document.body.classList.add("assistent-offen");
  eingabe.value = entwuerfe.get(ticket?.id) || vorgeschlageneFrage;
  if (eingabe.value) entwuerfe.set(ticket?.id, eingabe.value);
  zeichne();
  eingabe.focus();
}

export function aktualisiereAssistent(ticket) {
  if (panel.hidden) return;
  if (ticket === undefined) {
    schliessen();
    return;
  }
  if (kontext?.id === ticket?.id) return;
  kontext = ticket;
  eingabe.value = entwuerfe.get(ticket?.id) || "";
  zeichne();
}

function schliessen() {
  panel.hidden = true;
  document.body.classList.remove("assistent-offen");
  document.getElementById("assistent-oeffnen").focus();
}

function zeichne() {
  const id = kontext?.id;
  const verlauf = verlaeufe.get(id) || [];
  senden.disabled = wartend.has(id);
  eingabe.placeholder = kontext ? "Frage zu diesem Ticket …" : "Allgemeine IT-Frage stellen …";
  kontextZeile.textContent = kontext ? `${ticketNr(id)} ${kontext.titel}` : "Allgemeine IT-Hilfe";

  liste.replaceChildren();
  if (!verlauf.length) {
    liste.append(h("div", { class: "chat-leer" },
      h("div", { class: "vorschlaege" },
        (kontext ? ["Was ist der nächste Schritt?", "Gibt es einen ähnlichen gelösten Fall?"] : VORSCHLAEGE)
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
  if (wartend.has(id)) {
    liste.append(h("div", { class: "blase blase-ki blase-wartet" }, h("span", { class: "punkte" }, "KI denkt nach"), h("span", { class: "sekunden" })));
  }
  const letzte = liste.lastElementChild;
  if (letzte) liste.scrollTop += letzte.getBoundingClientRect().top - liste.getBoundingClientRect().top - 8;
}

async function fragen(text) {
  const frage = text.trim();
  const id = kontext?.id;
  if (!frage || wartend.has(id)) return;
  if (!verlaeufe.has(id)) verlaeufe.set(id, []);
  const verlauf = verlaeufe.get(id);
  const vorherigeFragen = verlauf.filter(n => n.rolle === "ich").slice(-6).map(n => n.text);
  eingabe.value = "";
  entwuerfe.delete(id);
  verlauf.push({ rolle: "ich", text: frage });
  wartend.add(id);
  zeichne();

  const start = Date.now();
  const uhr = setInterval(() => {
    const el = liste.querySelector(".sekunden");
    if (el && kontext?.id === id) el.textContent = ` ${Math.round((Date.now() - start) / 1000)} s`;
  }, 500);

  try {
    const r = id == null ? await api.frage(frage) : await api.frageTicket(id, frage, vorherigeFragen);
    const info = ANTWORTHERKUNFT[r.modus] || "";
    verlauf.push({ rolle: "ki", text: r.antwort, info, quellen: r.quellen });
  } catch (e) {
    verlauf.push({ rolle: "ki", text: `Fehler: ${e.message}`, info: "" });
  } finally {
    clearInterval(uhr);
    wartend.delete(id);
    if (!panel.hidden && kontext?.id === id) zeichne();
  }
}
