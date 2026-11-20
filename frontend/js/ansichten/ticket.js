// Ticket-Detail: links was vom Menschen kommt (Beschreibung, Verlauf, Bearbeiten),
// rechts was die KI beiträgt (Bewertung, Lösungsvorschlag) und die Kundendoku.

import { api } from "../api.js";
import { PRIORITAET, STATUS } from "../config.js";
import {
  alter, formatZeit, fuege, h, istSpamVerdacht, kiMarke, leeren, markdown, prioBadge, slaAmpel,
  statusBadge, ticketNr,
} from "../hilfen.js";
import {
  anzeigeName, kundeName, meldung, mitarbeiterListe, neuZeichnen, ticketErsetzen, zustand,
} from "../zustand.js";
import { oeffneAssistent } from "./assistent.js";

export function zeigeTicket(ziel, { teile }) {
  const id = Number(teile[0]);
  const t = zustand.tickets.find((x) => x.id === id);
  if (!t) {
    ziel.append(h("div", { class: "karte leer-zustand" },
      h("h2", {}, `Ticket #${teile[0] ?? ""} nicht gefunden`),
      h("a", { href: "#/tickets", class: "knopf" }, "Zur Ticketliste")));
    return "Ticket";
  }

  ziel.append(
    h("a", { href: "#/tickets", class: "zurueck" }, "← Alle Tickets"),
    h("div", { class: "ticket-kopf" },
      h("h2", {}, h("span", { class: "nr" }, ticketNr(t.id)), " ", t.titel),
      h("div", { class: "badges" },
        statusBadge(t.status),
        prioBadge(t.prioritaet, t.prioritaet_quelle),
        slaAmpel(t, true),
        istSpamVerdacht(t) ? h("span", { class: "badge badge-ki" }, "✦ Spam-Verdacht") : null)),
    h("div", { class: "raster-detail" },
      h("div", { class: "spalte" }, beschreibung(t), bearbeiten(t), verlauf(t)),
      h("div", { class: "spalte" }, kiBlock(t), kundeKarte(t))),
  );
  return `Ticket ${ticketNr(t.id)}`;
}

// --- Links: Mensch --------------------------------------------------------
function beschreibung(t) {
  return h("section", { class: "karte" },
    h("div", { class: "karte-kopf" },
      h("h3", {}, "Nachricht"),
      h("span", { class: "hinweis" }, `${kundeName(t.kunde)} · ${formatZeit(t.erstellt_am)} (${alter(t.erstellt_am)})`)),
    h("p", { class: "nachricht" }, t.beschreibung),
    t.loesungsweg ? h("div", { class: "loesung" }, h("h4", {}, "Lösungsweg"), h("p", {}, t.loesungsweg)) : null);
}

function bearbeiten(t) {
  const status = h("select", { id: "f-status" },
    Object.entries(STATUS).map(([w, txt]) => h("option", { value: w, selected: t.status === w }, txt)));

  const prio = h("select", { id: "f-prio" },
    h("option", { value: "", disabled: true, selected: !t.prioritaet }, "noch nicht bewertet"),
    Object.entries(PRIORITAET).map(([w, txt]) => h("option", { value: w, selected: t.prioritaet === w }, txt)));

  const bearbeiter = h("select", { id: "f-bearbeiter" },
    h("option", { value: "", selected: !t.zugewiesen_an }, "niemand"),
    mitarbeiterListe().map((m) => h("option", { value: m, selected: t.zugewiesen_an === m }, anzeigeName(m))));

  const loesung = h("textarea", {
    id: "f-loesung", rows: 3, maxlength: 4000,
    placeholder: "Was war die Ursache, was hat geholfen? Daraus lernt die KI für ähnliche Fälle.",
  });
  loesung.value = t.loesungsweg || "";

  const speichern = h("button", { class: "knopf knopf-haupt", type: "submit" }, "Speichern");
  const mir = zustand.mitarbeiter && zustand.mitarbeiter !== t.zugewiesen_an
    ? h("button", { class: "knopf", type: "button", title: "Mir zuweisen, neue Tickets gehen auf In Bearbeitung" }, "Übernehmen")
    : null;

  const senden = async (aenderung, text) => {
    if (!Object.keys(aenderung).length) {
      meldung("Nichts geändert.");
      return;
    }
    speichern.disabled = true;
    try {
      ticketErsetzen(await api.ticketAendern(t.id, aenderung));
      meldung(text, "erfolg");
      neuZeichnen();
    } catch (e) {
      meldung(e.message, "fehler");
      speichern.disabled = false;
    }
  };

  // Übernehmen: zuweisen und bei neuen Tickets gleich "In Bearbeitung" (stoppt die SLA)
  mir?.addEventListener("click", () => {
    const aenderung = { zugewiesen_an: zustand.mitarbeiter };
    if (t.status === "neu") aenderung.status = "in_bearbeitung";
    senden(aenderung, `Ticket ${ticketNr(t.id)} übernommen`);
  });

  const formular = h("form", { class: "formular" },
    h("div", { class: "formular-reihe" },
      h("label", { for: "f-status" }, "Status", status),
      h("label", { for: "f-prio" },
        "Priorität",
        prio,
        t.prioritaet_quelle === "manuell" ? h("span", { class: "feld-hinweis" }, "von Hand gesetzt") : null),
      h("label", { for: "f-bearbeiter" }, "Bearbeiter", bearbeiter)),
    h("label", { for: "f-loesung" }, "Lösungsweg", loesung),
    h("div", { class: "knopfreihe" }, speichern, mir));

  formular.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const aenderung = {};
    if (prio.value && prio.value !== t.prioritaet) aenderung.prioritaet = prio.value;
    if (bearbeiter.value !== (t.zugewiesen_an || "")) aenderung.zugewiesen_an = bearbeiter.value || null;
    if (loesung.value.trim() !== (t.loesungsweg || "")) aenderung.loesungsweg = loesung.value.trim();
    if (status.value !== t.status) {
      if (status.value === "geschlossen" && !loesung.value.trim() && t.spam_entscheidung !== "spam") {
        meldung("Zum Schließen bitte einen Lösungsweg eintragen.", "fehler");
        loesung.focus();
        return;
      }
      aenderung.status = status.value;
    }
    senden(aenderung, `Ticket ${ticketNr(t.id)} gespeichert`);
  });

  return h("section", { class: "karte" }, h("div", { class: "karte-kopf" }, h("h3", {}, "Bearbeiten")), formular);
}

function verlauf(t) {
  const eintraege = [...(t.statushistorie || [])].reverse();
  return h("section", { class: "karte" },
    h("div", { class: "karte-kopf" }, h("h3", {}, "Verlauf")),
    h("ol", { class: "verlauf" },
      eintraege.map((e) => h("li", {},
        statusBadge(e.status),
        h("span", { class: "gedimmt" }, `${formatZeit(e.seit)} (${alter(e.seit)})`)))));
}

// --- Rechts: KI -----------------------------------------------------------
function kiBlock(t) {
  const karte = h("section", { class: "karte karte-ki", "aria-labelledby": "t-ki" },
    h("div", { class: "karte-kopf" }, h("h3", { id: "t-ki" }, kiMarke("KI-Einschätzung"))));

  const knopf = h("button", { class: "knopf knopf-ki" }, t.ki ? "Neu bewerten" : "✦ Jetzt bewerten lassen");
  knopf.addEventListener("click", async () => {
    knopf.disabled = true;
    knopf.textContent = "KI bewertet …";
    try {
      const r = await api.analysieren(t.id);
      ticketErsetzen(await api.ticket(t.id));
      meldung(`Bewertet in ${(r.dauer_ms / 1000).toFixed(1)} s (${r.modus})`, "erfolg");
      neuZeichnen();
    } catch (e) {
      meldung(e.message, "fehler");
      knopf.disabled = false;
      knopf.textContent = "Erneut versuchen";
    }
  });

  if (!t.ki) {
    karte.append(h("p", { class: "leer" }, "Die KI hat dieses Ticket noch nicht bewertet."), knopf);
    return karte;
  }

  const ki = t.ki;
  const abweichung = t.prioritaet_quelle === "manuell" && t.prioritaet !== ki.prioritaet;

  fuege(karte,
    h("dl", { class: "werte" },
      h("dt", {}, "Priorität"), h("dd", {}, prioBadge(ki.prioritaet, "ki")),
      h("dt", {}, "Kategorie"), h("dd", {}, ki.kategorie || "–"),
      h("dt", {}, "Spam"), h("dd", {}, ki.spam ? h("strong", { class: "text-rot" }, "Ja") : "Nein")),
    abweichung
      ? h("p", { class: "feld-hinweis" },
        `Von Hand auf „${PRIORITAET[t.prioritaet]}“ gesetzt. Das hat Vorrang vor dem KI-Vorschlag.`)
      : null,
    ki.begruendung ? h("p", { class: "begruendung" }, h("strong", {}, "Begründung: "), ki.begruendung) : null,
    h("div", { class: "vorschlag" },
      h("h4", {}, "Lösungsvorschlag"),
      ki.loesungsvorschlag
        ? h("div", { class: "md" }, markdown(ki.loesungsvorschlag))
        : h("p", { class: "gedimmt" }, "Vorschläge aus ähnlichen gelösten Tickets folgen (RAG)."),
      ki.aehnliche_tickets?.length
        ? h("p", {}, "Ähnliche Fälle: ",
          ki.aehnliche_tickets.map((n, i) => [i ? ", " : "", h("a", { href: `#/ticket/${n}` }, ticketNr(n))]))
        : null),
    t.spam_entscheidung
      ? h("p", { class: "feld-hinweis" },
        t.spam_entscheidung === "spam" ? "Spam von einem Mitarbeiter bestätigt." : "Als „kein Spam“ markiert (Fehlalarm der KI).")
      : null,
    h("div", { class: "knopfreihe" },
      knopf,
      h("button", { class: "knopf", onclick: () => oeffneAssistent(t) }, "KI zu diesem Ticket fragen")),
    h("p", { class: "klein gedimmt" }, "KI-Vorschläge können falsch sein. Entscheidung immer durch einen Mitarbeiter."),
  );
  return karte;
}

// --- Rechts: Kunde und Doku -----------------------------------------------
function kundeKarte(t) {
  const karte = h("section", { class: "karte" }, h("div", { class: "karte-kopf" }, h("h3", {}, "Kunde")));
  const kunde = zustand.kunden.find((k) => k.kunde === t.kunde);
  if (!kunde) {
    karte.append(h("p", { class: "leer" }, "Absender keinem Kunden zugeordnet."));
    return karte;
  }

  const doku = h("div", { class: "doku md", hidden: true });
  const knopf = h("button", { class: "knopf", "aria-expanded": "false" }, "Kundendoku anzeigen");
  knopf.addEventListener("click", async () => {
    const offen = knopf.getAttribute("aria-expanded") === "true";
    if (offen) {
      doku.hidden = true;
      knopf.setAttribute("aria-expanded", "false");
      knopf.textContent = "Kundendoku anzeigen";
      return;
    }
    if (!doku.childNodes.length) {
      knopf.disabled = true;
      try {
        const d = await api.kundendoku(kunde.kunde);
        leeren(doku);
        doku.append(markdown(d.markdown));
      } catch (e) {
        meldung(e.message, "fehler");
        knopf.disabled = false;
        return;
      }
      knopf.disabled = false;
    }
    doku.hidden = false;
    knopf.setAttribute("aria-expanded", "true");
    knopf.textContent = "Kundendoku ausblenden";
  });

  karte.append(
    h("dl", { class: "werte" },
      h("dt", {}, "Name"), h("dd", {}, kunde.name),
      h("dt", {}, "Ort"), h("dd", {}, kunde.ort),
      h("dt", {}, "Ansprechpartner"), h("dd", {}, kunde.ansprechpartner)),
    h("p", { class: "klein gedimmt" }, "🔒 Zugangsdaten stehen nie in der Doku, nur der Verweis auf den Passwortmanager."),
    knopf, doku);
  return karte;
}
