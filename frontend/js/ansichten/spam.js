// Spam-Prüfung: Die KI markiert nur. Ein Mitarbeiter bestätigt (Ticket wird
// geschlossen) oder widerspricht (Ticket kommt zurück in den Handlungsbedarf).
// Gelöscht wird nichts, damit sich Fehlalarme später auswerten lassen.

import { api } from "../api.js";
import { alter, fuege, h, kiMarke, ticketNr } from "../hilfen.js";
import { kundeName, meldung, neuZeichnen, ticketErsetzen, zustand } from "../zustand.js";

export function zeigeSpam(ziel) {
  const offen = zustand.tickets
    .filter((t) => t.ki?.spam && !t.spam_entscheidung && t.status !== "geschlossen")
    .sort((a, b) => b.id - a.id);
  const bestaetigt = zustand.tickets.filter((t) => t.spam_entscheidung === "spam").length;
  const fehlalarme = zustand.tickets.filter((t) => t.spam_entscheidung === "kein_spam").length;
  const unbewertet = zustand.tickets.filter((t) => !t.ki?.prioritaet && t.status !== "geschlossen").length;

  fuege(ziel,
    h("div", { class: "hinweisleiste" },
      kiMarke(),
      h("span", {}, "Die KI schlägt vor, ein Mitarbeiter entscheidet. Nicht auf Links in verdächtigen Nachrichten klicken."),
      h("span", { class: "hinweisleiste-rechts" }, `Bestätigt: ${bestaetigt} · Fehlalarme: ${fehlalarme}`)),
    unbewertet
      ? h("p", { class: "hinweis" }, `${unbewertet} offene Tickets sind noch nicht bewertet und erscheinen erst danach hier. `,
        h("a", { href: "#/uebersicht", class: "link" }, "Zur Übersicht"))
      : null,
    offen.length
      ? h("div", { class: "spam-liste" }, offen.map(spamKarte))
      : h("div", { class: "karte leer-zustand" }, h("p", {}, "Keine offenen Spam-Verdachtsfälle.")),
  );
}

function spamKarte(t) {
  const knoepfe = [];
  const entscheiden = async (aenderung, text, link) => {
    knoepfe.forEach((k) => { k.disabled = true; });
    try {
      ticketErsetzen(await api.ticketAendern(t.id, aenderung));
      meldung(text, "erfolg", link);
      neuZeichnen();
    } catch (e) {
      meldung(e.message, "fehler");
      knoepfe.forEach((k) => { k.disabled = false; });
    }
  };

  const ja = h("button", { class: "knopf knopf-gefahr" }, "Spam bestätigen und schließen");
  ja.addEventListener("click", () =>
    entscheiden({ spam_entscheidung: "spam", status: "geschlossen" }, `${ticketNr(t.id)} als Spam geschlossen`));

  const nein = h("button", { class: "knopf" }, "Kein Spam");
  nein.addEventListener("click", () =>
    entscheiden({ spam_entscheidung: "kein_spam" }, `${ticketNr(t.id)} ist zurück im Handlungsbedarf.`,
      { href: `#/ticket/${t.id}`, text: "Priorität festlegen" }));

  knoepfe.push(ja, nein);

  return h("article", { class: "karte spam-karte" },
    h("div", { class: "karte-kopf" },
      h("h3", {}, h("a", { href: `#/ticket/${t.id}` }, ticketNr(t.id)), " ", t.titel),
      h("span", { class: "hinweis" }, `${kundeName(t.kunde)} · ${alter(t.erstellt_am)}`)),
    h("p", { class: "nachricht vorschau" }, t.beschreibung),
    h("p", { class: "begruendung ki-hinterlegt" }, kiMarke("Begründung"), " ", t.ki.begruendung || t.ki.loesungsvorschlag || "–"),
    h("div", { class: "knopfreihe" }, ja, nein));
}
