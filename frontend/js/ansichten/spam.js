// Modellvorschläge und manuelle Entscheidungen zur Spamprüfung.

import { api } from "../api.js";
import { STATUS } from "../config.js";
import { alter, h, istImSpamfilter, spamBadge, spamOffen, ticketNr } from "../hilfen.js";
import { kundeName, meldung, neuZeichnen, ticketErsetzen, zustand } from "../zustand.js";

export function zeigeSpam(ziel) {
  const offen = zustand.tickets
    .filter(spamOffen)
    .sort((a, b) => b.id - a.id);
  const bestaetigt = zustand.tickets.filter((t) => t.spam_entscheidung === "spam").length;
  const freigegeben = zustand.tickets.filter((t) =>
    t.status !== "geschlossen" && t.ki?.spam === true && t.spam_entscheidung === "kein_spam");

  ziel.append(
    h("div", { class: "hinweisleiste" },
      h("span", {}, "Hier erscheinen Spam- und Werbeverdachte aus der Ticketbewertung. Der Support entscheidet über die Freigabe."),
      h("span", { class: "hinweisleiste-rechts" }, `Bestätigt: ${bestaetigt}`)),
    offen.length
      ? h("div", { class: "spam-liste" }, offen.map(spamKarte))
      : h("div", { class: "karte leer-zustand" }, h("p", {}, "Keine offenen Spam-Verdachtsfälle.")),
  );
  if (freigegeben.length) {
    ziel.append(h("details", { class: "karte nachrichtenaktionen" },
      h("summary", {}, `Vom Support freigegeben (${freigegeben.length})`),
      h("p", { class: "hinweis" }, "Die Freigabe lässt sich im Ticket aufheben."),
      h("ul", {}, freigegeben.map((t) => h("li", {},
        h("a", { href: `#/ticket/${t.id}` }, ticketNr(t.id), " ", t.titel))))));
  }
}

function spamKarte(t) {
  return h("article", { class: "karte spam-karte" },
    h("div", { class: "karte-kopf" },
      h("h3", {}, h("a", { href: `#/ticket/${t.id}` }, ticketNr(t.id), " ", t.titel)),
      h("span", { class: "hinweis" }, `${kundeName(t.kunde)} · ${alter(t.erstellt_am)}`)),
    h("p", { class: "nachricht vorschau" }, t.beschreibung),
    spamBadge(t),
    h("p", { class: "begruendung" }, t.ki.begruendung || "Keine Begründung hinterlegt."),
    spamAktionen(t));
}

export function spamAktionen(t) {
  const knoepfe = [];
  const entscheiden = async (aenderung, text, link) => {
    knoepfe.forEach((k) => { k.disabled = true; });
    try {
      const aktuell = await api.ticketAendern(t.id, {
        ...aenderung,
        erwartete_spam_entscheidung: t.spam_entscheidung ?? null,
        erwarteter_status: t.status,
      });
      ticketErsetzen(aktuell);
      meldung(typeof text === "function" ? text(aktuell) : text, "erfolg", link);
      neuZeichnen();
    } catch (e) {
      if (e.code === 409) {
        try {
          const aktuell = await api.ticket(t.id);
          ticketErsetzen(aktuell);
          neuZeichnen();
          meldung(`${ticketNr(t.id)} wurde inzwischen geändert. Aktueller Status: ${STATUS[aktuell.status]}.`, "info",
            { href: `#/ticket/${t.id}`, text: "Ticket öffnen" });
        } catch (ladefehler) {
          meldung(`${ticketNr(t.id)} wurde inzwischen geändert. Bitte die Seite neu laden. ${ladefehler.message}`, "fehler");
        }
      } else {
        meldung(e.message, "fehler");
      }
      knoepfe.forEach((k) => { k.disabled = false; });
    }
  };

  if (t.spam_entscheidung === "kein_spam" && t.status !== "geschlossen") {
    const pruefen = h("button", { type: "button", class: "knopf" }, "Freigabe aufheben");
    pruefen.addEventListener("click", () => entscheiden({ spam_entscheidung: null },
      (aktuell) => spamOffen(aktuell) ? `${ticketNr(t.id)} wurde nach Spam / Werbung verschoben.` :
        `${ticketNr(t.id)} bleibt im Support.`));
    knoepfe.push(pruefen);
  }
  if (t.spam_entscheidung !== "spam") {
    const text = t.status === "geschlossen" ? "Spam bestätigen" :
      spamOffen(t) ? "Spam bestätigen und schließen" : "Als Spam markieren und schließen";
    const ja = h("button", { type: "button", class: "knopf knopf-gefahr" }, text);
    ja.addEventListener("click", () => entscheiden(
      { spam_entscheidung: "spam", status: "geschlossen" }, `${ticketNr(t.id)} als Spam geschlossen.`));
    knoepfe.push(ja);
  }
  if (istImSpamfilter(t)) {
    const wiederOeffnen = t.status === "geschlossen" && t.spam_entscheidung === "spam";
    const aenderung = { spam_entscheidung: "kein_spam" };
    if (wiederOeffnen) aenderung.status = "neu";
    const nein = h("button", { type: "button", class: "knopf" }, wiederOeffnen ? "Als Supportticket wieder öffnen" : "Kein Spam");
    nein.addEventListener("click", () => entscheiden(aenderung, `${ticketNr(t.id)} für den Support freigegeben.`,
      { href: `#/ticket/${t.id}`, text: "Ticket öffnen" }));
    knoepfe.push(nein);
  }
  return h("div", { class: "knopfreihe" }, knoepfe);
}
