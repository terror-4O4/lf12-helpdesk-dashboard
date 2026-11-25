// Übersicht: Kennzahlen, Handlungsbedarf, eigene Tickets, persönliche To-dos.
// Ziel laut Antrag: alles Wichtige auf einen Blick, ohne Scrollen.

import { api } from "../api.js";
import { PRIORITAET, STATUS } from "../config.js";
import {
  alter, fuege, h, hatHandlungsbedarf, istOffen, istImSpamfilter, jetzt, kiMarke, leeren, nachDringlichkeit, sla,
  slaAmpel, spamOffen, ticketNr, ticketPrioBadge,
} from "../hilfen.js";
import {
  anzeigeName, kundeName, lokalLesen, lokalSchreiben, meldung, neuZeichnen, ticketErsetzen, zustand,
} from "../zustand.js";
import { ticketTabelle } from "./tickets.js";

export function zeigeUebersicht(ziel) {
  const alle = zustand.tickets;
  const bezugszeit = jetzt();
  const offen = alle.filter((t) => istOffen(t) && !istImSpamfilter(t));
  const handlungsbedarf = offen
    .filter(hatHandlungsbedarf)
    .sort((a, b) => nachDringlichkeit(a, b, bezugszeit));
  const unbewertet = offen.filter((t) => !t.ki?.prioritaet);

  fuege(ziel,
    kennzahlen(alle, offen, bezugszeit),
    unbewertet.length ? hinweisUnbewertet(unbewertet) : null,
    h("div", { class: "raster-uebersicht" },
      h("section", { class: "karte", "aria-labelledby": "t-handlung" },
        h("div", { class: "karte-kopf" },
          h("h2", { id: "t-handlung" }, "Handlungsbedarf"),
          h("span", { class: "hinweis" }, "Neu und Antwort erhalten, dringendste zuerst")),
        handlungsbedarf.length
          ? ticketTabelle(handlungsbedarf, { kompakt: true, bezugszeit })
          : h("p", { class: "leer" }, "Nichts offen. 🎉")),
      h("div", { class: "spalte" },
        meineTickets(offen, bezugszeit),
        todos())),
  );
}

// --- Kennzahlen -----------------------------------------------------------
function kennzahlen(alle, offen, bezugszeit) {
  const kachel = (titel, wert, link, art = "") =>
    h("a", { class: `kachel ${art}`, href: link },
      h("span", { class: "kachel-wert" }, String(wert)),
      h("span", { class: "kachel-titel" }, titel));

  const zaehle = (fn) => offen.filter(fn).length;
  const slaRot = zaehle((t) => sla(t, bezugszeit).zustand === "rot");
  const sehrHoch = zaehle((t) => t.prioritaet === "sehr_hoch");
  const spam = alle.filter(spamOffen).length;

  return h("div", { class: "kacheln", role: "list" },
    kachel("Neu", zaehle((t) => t.status === "neu"), "#/tickets?status=neu"),
    kachel("Antwort erhalten", zaehle((t) => t.status === "antwort_erhalten"), "#/tickets?status=antwort_erhalten"),
    kachel("In Bearbeitung", zaehle((t) => t.status === "in_bearbeitung"), "#/tickets?status=in_bearbeitung"),
    kachel(PRIORITAET.sehr_hoch, sehrHoch, "#/tickets?prioritaet=sehr_hoch", sehrHoch ? "kachel-warn" : ""),
    kachel("SLA überschritten", slaRot, "#/tickets?sla=rot", slaRot ? "kachel-rot" : ""),
    kachel("Spam / Werbung", spam, "#/spam"),
  );
}

// --- Noch nicht bewertete Tickets -----------------------------------------
function hinweisUnbewertet(liste) {
  const text = h("span", {}, `${liste.length} offene Tickets sind noch nicht von der KI bewertet.`);
  const knopf = h("button", { class: "knopf knopf-ki" }, "✦ Jetzt bewerten lassen");

  knopf.addEventListener("click", async () => {
    knopf.disabled = true;
    let fertig = 0;
    let fehler = 0;
    for (const t of liste) {
      knopf.textContent = `KI bewertet … ${fertig + 1}/${liste.length}`;
      try {
        await api.analysieren(t.id);
        ticketErsetzen(await api.ticket(t.id));
      } catch (e) {
        fehler += 1;
        if (fehler === 1) meldung(`#${t.id}: ${e.message}`, "fehler");
      }
      fertig += 1;
    }
    meldung(`${fertig - fehler} von ${liste.length} Tickets bewertet.`, fehler ? "fehler" : "erfolg");
    neuZeichnen();
  });

  return h("div", { class: "hinweisleiste" }, kiMarke(), text, knopf);
}

// --- Meine Tickets --------------------------------------------------------
function meineTickets(offen, bezugszeit) {
  const ich = zustand.mitarbeiter;
  const karte = h("section", { class: "karte", "aria-labelledby": "t-meine" },
    h("div", { class: "karte-kopf" },
      h("h2", { id: "t-meine" }, ich ? `Meine Tickets (${anzeigeName(ich)})` : "Meine Tickets")));

  if (!ich) {
    karte.append(h("p", { class: "leer" }, "Oben rechts einen Mitarbeiter wählen."));
    return karte;
  }

  const meine = offen.filter((t) => t.zugewiesen_an === ich)
    .sort((a, b) => nachDringlichkeit(a, b, bezugszeit));
  if (!meine.length) {
    karte.append(h("p", { class: "leer" }, "Dir ist gerade nichts zugewiesen."));
    return karte;
  }

  karte.append(h("ul", { class: "liste-kurz" },
    meine.map((t) => h("li", {},
      h("a", { href: `#/ticket/${t.id}`, class: "zeile-link" },
        slaAmpel(t, false, bezugszeit),
        h("span", { class: "nr" }, ticketNr(t.id)),
        h("span", { class: "titel-kurz" }, t.titel),
        ticketPrioBadge(t)),
      h("span", { class: "unterzeile" }, `${kundeName(t.kunde)} · ${STATUS[t.status]} · ${alter(t.erstellt_am, bezugszeit)}`)))));
  return karte;
}

// --- Persönliche To-dos ---------------------------------------------------
// Bis es ein Format im Backend gibt, nur im Browser gespeichert (pro Mitarbeiter).
function todos() {
  const schluessel = `todos.${zustand.mitarbeiter || "allgemein"}`;
  let eintraege = lokalLesen(schluessel, []);

  const liste = h("ul", { class: "todos" });
  const eingabe = h("input", {
    type: "text", placeholder: "z. B. Rückruf Logistik 14 Uhr", maxlength: 200,
    "aria-label": "Neues To-do",
  });

  const speichern = () => lokalSchreiben(schluessel, eintraege);

  const zeichneListe = () => {
    leeren(liste);
    if (!eintraege.length) liste.append(h("li", { class: "leer" }, "Keine To-dos."));
    eintraege.forEach((e, i) => {
      const haken = h("input", { type: "checkbox", checked: e.erledigt, "aria-label": "Erledigt" });
      haken.addEventListener("change", () => {
        e.erledigt = haken.checked;
        speichern();
        zeichneListe();
      });
      liste.append(h("li", { class: e.erledigt ? "erledigt" : "" },
        h("label", {}, haken, h("span", {}, e.text)),
        h("button", {
          class: "knopf-klein", "aria-label": "To-do löschen",
          onclick: () => { eintraege.splice(i, 1); speichern(); zeichneListe(); },
        }, "×")));
    });
  };

  const formular = h("form", { class: "todo-neu" }, eingabe, h("button", { class: "knopf", type: "submit" }, "Hinzufügen"));
  formular.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const text = eingabe.value.trim();
    if (!text) return;
    eintraege = [...eintraege, { text, erledigt: false }];
    speichern();
    eingabe.value = "";
    zeichneListe();
  });

  zeichneListe();
  return h("section", { class: "karte", "aria-labelledby": "t-todos" },
    h("div", { class: "karte-kopf" },
      h("h2", { id: "t-todos" }, "Meine To-dos"),
      h("span", { class: "hinweis", title: "Wird nicht ans Backend geschickt" }, "nur in diesem Browser")),
    liste, formular);
}
