// Einstieg: Navigation (Router), Kopfzeile, KI-Status.
// Die einzelnen Ansichten liegen in js/ansichten/.

import { api } from "./api.js";
import { STATUS_ABFRAGE_MS } from "./config.js";
import { h, istDemoZeit, jetzt, formatZeit, leeren, spamOffen } from "./hilfen.js";
import {
  anzeigeName, ladeDaten, meldung, mitarbeiterListe, mitarbeiterSetzen, setzeZeichner, zustand,
} from "./zustand.js";
import { zeigeUebersicht } from "./ansichten/uebersicht.js";
import { zeigeTickets } from "./ansichten/tickets.js";
import { zeigeTicket } from "./ansichten/ticket.js";
import { zeigeSpam } from "./ansichten/spam.js";
import { oeffneNeuesTicket } from "./ansichten/neues-ticket.js";
import { initAssistent, oeffneAssistent } from "./ansichten/assistent.js";

const ANSICHTEN = {
  uebersicht: { titel: "Übersicht", zeige: zeigeUebersicht },
  tickets: { titel: "Tickets", zeige: zeigeTickets },
  ticket: { titel: "Ticket", zeige: zeigeTicket, nav: "tickets" },
  spam: { titel: "Spam-Prüfung", zeige: zeigeSpam },
};

// "#/tickets?status=neu" -> { name: "tickets", teile: [], abfrage: URLSearchParams }
function leseAdresse() {
  const [pfad, abfrage = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const [name, ...teile] = pfad.split("/").filter(Boolean);
  return { name: ANSICHTEN[name] ? name : "uebersicht", teile, abfrage: new URLSearchParams(abfrage) };
}

let zeichnet = false;
let nochmal = null; // Wunsch zum Neuzeichnen, während gerade gezeichnet wird

async function zeichnen({ neuLaden = true } = {}) {
  if (zeichnet) {
    nochmal = { neuLaden: neuLaden || nochmal?.neuLaden };
    return;
  }
  zeichnet = true;
  const ziel = document.getElementById("inhalt");
  const adresse = leseAdresse();
  const ansicht = ANSICHTEN[adresse.name];

  for (const a of document.querySelectorAll("#nav a")) {
    const aktiv = a.dataset.ansicht === (ansicht.nav || adresse.name);
    a.classList.toggle("aktiv", aktiv);
    if (aktiv) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }

  try {
    if (neuLaden) await ladeDaten();
    aktualisiereKopf();
    leeren(ziel);
    const titel = await ansicht.zeige(ziel, adresse);
    setzeTitel(titel || ansicht.titel);
  } catch (fehler) {
    leeren(ziel);
    ziel.append(
      h("div", { class: "karte leer-zustand" },
        h("h2", {}, "Daten konnten nicht geladen werden"),
        h("p", {}, fehler.message),
        h("button", { class: "knopf", onclick: () => zeichnen() }, "Erneut versuchen")),
    );
  } finally {
    zeichnet = false;
    if (nochmal) {
      const wunsch = nochmal;
      nochmal = null;
      zeichnen(wunsch);
    }
  }
}

function setzeTitel(titel) {
  document.getElementById("seitentitel").textContent = titel;
  document.title = `${titel} · Helpdesk-Dashboard`;
}

function aktualisiereKopf() {
  // Spam-Zähler in der Seitenleiste
  const anzahl = zustand.tickets.filter(spamOffen).length;
  const zaehler = document.getElementById("spam-zaehler");
  zaehler.textContent = anzahl;
  zaehler.hidden = anzahl === 0;

  // Mitarbeiter-Auswahl
  const auswahl = document.getElementById("mitarbeiter");
  leeren(auswahl);
  auswahl.append(h("option", { value: "" }, "Mitarbeiter wählen"));
  for (const m of mitarbeiterListe()) {
    auswahl.append(h("option", { value: m, selected: m === zustand.mitarbeiter }, anzeigeName(m)));
  }
}

async function pruefeKiStatus() {
  const el = document.getElementById("ki-status");
  const fuss = document.getElementById("fuss-modell");
  try {
    const s = await api.status();
    zustand.kiStatus = s;
    if (s.ki_modus === "mock") {
      el.textContent = "KI: Mock";
      el.className = "ki-status ki-mock";
      el.title = "Beispielantworten ohne KI-Server (KI_MOCK=true in der .env)";
      fuss.textContent = "KI im Mock-Modus";
    } else if (s.ki_erreichbar && s.embedding_erreichbar === false) {
      el.textContent = "KI online, Fallsuche aus";
      el.className = "ki-status ki-mock";
      el.title = "Chat-Modell erreichbar, Embedding-Server (EMBED_URL) nicht: ähnliche Fälle können nicht gesucht werden";
      fuss.textContent = s.ki_modell ? `Modell: ${s.ki_modell} (llama.cpp)` : "llama.cpp";
    } else if (s.ki_erreichbar) {
      el.textContent = "KI online";
      el.className = "ki-status ki-online";
      el.title = s.ki_modell ? `Modell: ${s.ki_modell}` : "Lokaler llama-server erreichbar";
      fuss.textContent = s.ki_modell ? `Modell: ${s.ki_modell} (llama.cpp)` : "llama.cpp";
    } else {
      el.textContent = "KI nicht erreichbar";
      el.className = "ki-status ki-aus";
      el.title = "Backend läuft, aber der llama-server antwortet nicht";
      fuss.textContent = "";
    }
  } catch {
    zustand.kiStatus = null;
    el.textContent = "Backend nicht erreichbar";
    el.className = "ki-status ki-aus";
    el.title = "";
    fuss.textContent = "";
  }
}

function start() {
  setzeZeichner(() => zeichnen({ neuLaden: false }));

  document.getElementById("neues-ticket").addEventListener("click", oeffneNeuesTicket);
  document.getElementById("assistent-oeffnen").addEventListener("click", () => oeffneAssistent());
  document.getElementById("mitarbeiter").addEventListener("change", (e) => {
    mitarbeiterSetzen(e.target.value);
    meldung(e.target.value ? `Angemeldet als ${anzeigeName(e.target.value)}` : "Kein Mitarbeiter gewählt");
    zeichnen({ neuLaden: false });
  });

  if (istDemoZeit()) {
    const el = document.getElementById("demo-zeit");
    el.textContent = `Demo-Zeit: ${formatZeit(jetzt().toISOString())}`;
    el.title = "Feste Uhrzeit für die Demo (Adresse ?jetzt=... oder DEMO_JETZT in config.js)";
    el.hidden = false;
  }

  initAssistent();
  window.addEventListener("hashchange", () => {
    zeichnen();
    document.getElementById("inhalt").focus({ preventScroll: true });
  });

  pruefeKiStatus();
  setInterval(pruefeKiStatus, STATUS_ABFRAGE_MS);
  zeichnen();
}

start();
