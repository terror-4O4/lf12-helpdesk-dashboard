// Ticket-Detail: links was vom Menschen kommt (Beschreibung, Verlauf, Bearbeiten),
// rechts was die KI beiträgt (Bewertung, Lösungsvorschlag) und die Kundendoku.

import { api } from "../api.js";
import { PRIORITAET, STATUS } from "../config.js";
import {
  alter, dauer, dokuQuellen, formatZeit, fuege, h, istImSpamfilter, jetzt, kiMarke, leeren, markdown, prioBadge, slaAmpel,
  spamBadge, statusBadge, ticketNr, ticketPrioBadge, wartezeit,
} from "../hilfen.js";
import {
  anzeigeName, kundeName, meldung, mitarbeiterListe, neuZeichnen, ticketErsetzen, zustand,
} from "../zustand.js";
import { oeffneAssistent } from "./assistent.js";
import { spamAktionen } from "./spam.js";

export function zeigeTicket(ziel, { teile }) {
  const id = Number(teile[0]);
  const t = zustand.tickets.find((x) => x.id === id);
  if (!t) {
    ziel.append(h("div", { class: "karte leer-zustand" },
      h("h2", {}, `Ticket #${teile[0] ?? ""} nicht gefunden`),
      h("a", { href: "#/tickets", class: "knopf" }, "Zur Ticketliste")));
    return "Ticket";
  }

  const bezugszeit = jetzt();
  const warten = wartezeit(t, bezugszeit);
  const imFilter = istImSpamfilter(t);
  ziel.append(
    h("a", { href: "#/tickets", class: "zurueck" }, "← Alle Tickets"),
    h("div", { class: "ticket-kopf" },
      h("h2", {}, h("span", { class: "nr" }, ticketNr(t.id)), " ", t.titel),
      h("div", { class: "badges" },
        statusBadge(t.status),
        imFilter ? null : ticketPrioBadge(t),
        slaAmpel(t, true, bezugszeit),
        warten ? h("span", { class: "hinweis" }, `Wartezeit auf ${warten.auf}: ${dauer(warten.minuten)}`) : null,
        spamBadge(t))),
    h("div", { class: "raster-detail" },
      h("div", { class: "spalte" }, beschreibung(t, bezugszeit), imFilter ? null : bearbeiten(t), verlauf(t, bezugszeit)),
      h("div", { class: "spalte" },
        imFilter ? h("section", { class: "karte" },
          h("div", { class: "karte-kopf" }, h("h3", {}, "Spam / Werbung")),
          t.spam_entscheidung === "spam" ? h("p", {}, "Vom Support als Spam bestätigt.") : null,
          spamAktionen(t)) : null,
        kiBlock(t),
        t.regelhinweise?.length ? h("section", { class: "karte" },
          h("h3", {}, "Regelhinweise"),
          h("ul", {}, t.regelhinweise.map(text => h("li", {}, text)))) : null,
        imFilter ? null : [kiFaelle(t), kundeKarte(t)])),
  );
  return `Ticket ${ticketNr(t.id)}`;
}

// --- Links: Mensch --------------------------------------------------------
function beschreibung(t, bezugszeit) {
  return h("section", { class: "karte" },
    h("div", { class: "karte-kopf" },
      h("h3", {}, "Nachricht"),
      h("span", { class: "hinweis" }, `${kundeName(t.kunde)} · ${formatZeit(t.erstellt_am)} (${alter(t.erstellt_am, bezugszeit)})`)),
    h("p", { class: "nachricht" }, t.beschreibung),
    t.ursache || t.loesungsweg
      ? h("div", { class: "loesung" },
        t.ursache ? [h("h4", {}, "Ursache"), h("p", {}, t.ursache)] : null,
        t.loesungsweg ? [h("h4", {}, "Lösungsweg"), h("p", {}, t.loesungsweg)] : null)
      : null,
    t.spam_entscheidung === "kein_spam" ? h("p", { class: "feld-hinweis" },
      t.status === "geschlossen" ? "Vom Support freigegeben." :
        "Als Supportticket freigegeben. Die Freigabe hat Vorrang vor dem Spam-Vorschlag.") : null,
    t.status !== "geschlossen" && !istImSpamfilter(t)
      ? h("details", { class: "nachrichtenaktionen", open: t.spam_entscheidung === "kein_spam" },
        h("summary", {}, "Nachrichtenaktionen"), spamAktionen(t)) : null);
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

  const ursache = h("textarea", {
    id: "f-ursache", rows: 2, maxlength: 1000,
    placeholder: "Was war die Ursache? z. B. Add-In nach Update fehlerhaft",
  });
  ursache.value = t.ursache || "";
  const loesung = h("textarea", {
    id: "f-loesung", rows: 3, maxlength: 4000,
    placeholder: "Was hat geholfen? Kurze Schritte, damit Kollegen es nachmachen können.",
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

  const abschluss = h("details", { class: "abschluss" },
    h("summary", {}, "Ursache und Lösungsweg"),
    h("label", { for: "f-ursache" }, "Ursache", ursache),
    h("label", { for: "f-loesung" }, "Lösungsweg", loesung),
    h("p", { class: "feld-hinweis" },
      "Beim Schließen wird der Lösungsweg in die Wissensbasis übernommen. Bitte Zugangsdaten weglassen."));
  status.addEventListener("change", () => {
    if (status.value === "geschlossen") abschluss.open = true;
  });

  const formular = h("form", { class: "formular" },
    h("div", { class: "formular-reihe" },
      h("label", { for: "f-status" }, "Status", status),
      h("label", { for: "f-prio" },
        "Priorität",
        prio,
        t.prioritaet_quelle === "manuell" ? h("span", { class: "feld-hinweis" }, "von Hand gesetzt") : null),
      h("label", { for: "f-bearbeiter" }, "Bearbeiter", bearbeiter)),
    abschluss,
    h("div", { class: "knopfreihe" }, speichern, mir));

  formular.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const aenderung = {};
    if (prio.value && prio.value !== t.prioritaet) aenderung.prioritaet = prio.value;
    if (bearbeiter.value !== (t.zugewiesen_an || "")) aenderung.zugewiesen_an = bearbeiter.value || null;
    if (ursache.value.trim() !== (t.ursache || "")) aenderung.ursache = ursache.value.trim();
    if (loesung.value.trim() !== (t.loesungsweg || "")) aenderung.loesungsweg = loesung.value.trim();
    if (status.value !== t.status) {
      if (status.value === "geschlossen" && !loesung.value.trim() && t.spam_entscheidung !== "spam") {
        meldung("Zum Schließen bitte einen Lösungsweg eintragen.", "fehler");
        abschluss.open = true;
        loesung.focus();
        return;
      }
      aenderung.status = status.value;
    }
    senden(aenderung, `Ticket ${ticketNr(t.id)} gespeichert`);
  });

  return h("section", { class: "karte" }, h("div", { class: "karte-kopf" }, h("h3", {}, "Bearbeiten")), formular);
}

function verlauf(t, bezugszeit) {
  const eintraege = [...(t.statushistorie || [])].reverse();
  return h("section", { class: "karte" },
    h("div", { class: "karte-kopf" }, h("h3", {}, "Verlauf")),
    h("ol", { class: "verlauf" },
      eintraege.map((e) => h("li", {},
        statusBadge(e.status),
        h("span", { class: "gedimmt" }, `${formatZeit(e.seit)} (${alter(e.seit, bezugszeit)})`)))));
}

// --- Rechts: KI -----------------------------------------------------------
function kiBlock(t) {
  const demo = t.ki?.modus === "mock";
  const karte = h("section", { class: demo ? "karte" : "karte karte-ki", "aria-labelledby": "t-ki" },
    h("div", { class: "karte-kopf" }, h("h3", { id: "t-ki" },
      demo ? "Demo-Bewertung (ohne Sprachmodell)" : kiMarke("KI-Einschätzung"))));
  const bewertet = Boolean(t.ki?.prioritaet);
  const knopf = h("button", { class: "knopf knopf-ki" }, bewertet ? "✦ Neu bewerten" : "✦ Jetzt bewerten lassen");
  const chat = istImSpamfilter(t) ? null : h("button", {
    class: "knopf knopf-ki", onclick: () => oeffneAssistent(t),
  }, "✦ Assistent öffnen");
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

  if (!bewertet) {
    karte.append(h("p", { class: "leer" }, "Die KI hat dieses Ticket noch nicht bewertet."),
      h("div", { class: "knopfreihe" }, t.spam_entscheidung === "spam" ? null : knopf, chat));
    return karte;
  }

  const ki = t.ki;
  const abweichung = t.prioritaet_quelle === "manuell" && t.prioritaet !== ki.prioritaet;

  fuege(karte,
    h("dl", { class: "werte" },
      h("dt", {}, "Priorität"), h("dd", {}, prioBadge(ki.prioritaet, demo ? "mock" : "ki")),
      h("dt", {}, "Kategorie"), h("dd", {}, ki.kategorie || "–"),
      h("dt", {}, "Spam"), h("dd", {}, ki.spam === true ? "Ja" : ki.spam === false ? "Nein" : "–")),
    abweichung
      ? h("p", { class: "feld-hinweis" },
        `Der Support hat die gültige Priorität auf „${PRIORITAET[t.prioritaet]}“ gesetzt.`)
      : null,
    ki.begruendung ? h("p", { class: "begruendung" }, h("strong", {}, "Begründung: "), ki.begruendung) : null,
    h("div", { class: "knopfreihe" }, t.spam_entscheidung === "spam" ? null : knopf, chat),
    h("p", { class: "klein gedimmt" }, "KI-Vorschläge können falsch sein. Entscheidung immer durch einen Mitarbeiter."),
  );
  return karte;
}

// --- Rechts: Ähnliche gelöste Fälle (RAG) -----------------------------------
function kiFaelle(t) {
  const ki = t.ki || {};
  const gesucht = Boolean(ki.loesungsvorschlag || ki.treffer?.length || ki.ursachen?.length);
  const modell = ki.loesungsmodus === "llama";
  const titeltext = "Ähnliche gelöste Fälle";
  const karte = h("section", { class: modell ? "karte karte-ki" : "karte", "aria-labelledby": "t-faelle" },
    h("div", { class: "karte-kopf" }, h("h3", { id: "t-faelle" }, modell ? kiMarke(titeltext) : titeltext)));

  const knopf = h("button", { class: "knopf knopf-ki" }, gesucht ? "✦ Neu suchen" : "✦ Ähnliche Fälle suchen");
  knopf.addEventListener("click", async () => {
    knopf.disabled = true;
    knopf.textContent = "Suche und KI laufen …";
    try {
      const r = await api.loesungsvorschlag(t.id);
      ticketErsetzen(await api.ticket(t.id));
      const anzahl = r.ergebnis.vorschlaege.length;
      meldung(anzahl
        ? `${anzahl} ${anzahl === 1 ? "Vorschlag" : "Vorschläge"} in ${(r.dauer_ms / 1000).toFixed(1)} s`
        : "Kein passender gelöster Fall gefunden", anzahl ? "erfolg" : "info");
      neuZeichnen();
    } catch (e) {
      meldung(e.message, "fehler");
      knopf.disabled = false;
      knopf.textContent = "Erneut versuchen";
    }
  });

  if (!gesucht) {
    karte.append(
      h("p", { class: "leer" }, "Sucht in bereits gelösten Tickets nach demselben Problem, bevorzugt beim selben Kunden."),
      knopf);
    return karte;
  }

  if (ki.loesungsmodus === "mock") {
    karte.append(h("p", { class: "feld-hinweis" }, "Demo-Auswahl aus gespeicherten Fällen."));
  } else if (!ki.loesungsmodus) {
    karte.append(h("p", { class: "feld-hinweis" }, "Für diesen gespeicherten Vorschlag ist die Herkunft nicht hinterlegt."));
  }

  const aehnlichkeit = Object.fromEntries((ki.treffer || []).map((x) => [x.id, x.aehnlichkeit]));
  const titel = (id) => zustand.tickets.find((x) => x.id === id)?.titel || "";
  const verweis = (id) => h("a", { href: `#/ticket/${id}`, title: titel(id) },
    ticketNr(id),
    aehnlichkeit[id] !== undefined ? ` (${Math.round(aehnlichkeit[id] * 100)} %)` : "");

  if (ki.ursachen?.length) {
    karte.append(h("ol", { class: "ursachen" }, ki.ursachen.map((u) => h("li", {},
      h("p", { class: "ursache" }, u.ursache),
      h("p", { class: "loesungsweg" }, u.loesungsweg),
      h("p", { class: "quelle" }, "aus ", u.tickets.map((id, i) => [i ? ", " : "", verweis(id)]))))));
  } else if (ki.loesungsvorschlag) {
    karte.append(h("div", { class: "md" }, markdown(ki.loesungsvorschlag)));
  }

  const weitere = (ki.treffer || []).filter((x) => !(ki.aehnliche_tickets || []).includes(x.id));
  if (weitere.length) {
    karte.append(h("p", { class: "klein gedimmt" }, "Weitere Treffer: ",
      weitere.map((x, i) => [i ? ", " : "", verweis(x.id)])));
  }
  karte.append(
    h("div", { class: "knopfreihe" }, knopf),
    h("p", { class: "klein gedimmt" }, "Vorschläge stammen nur aus gelösten Tickets. Vor dem Anwenden prüfen."));
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

  const fundstellen = h("div", { "aria-live": "polite" });
  const ladeFundstellen = async () => {
    fundstellen.replaceChildren(h("p", { class: "leer" }, "Suche passende Fundstellen …"));
    try {
      const ergebnis = await api.ticketDoku(t.id);
      fundstellen.replaceChildren(dokuQuellen(ergebnis.quellen) ||
        h("p", { class: "leer" }, "Keine passende Fundstelle in der Kundendoku."));
    } catch (e) {
      fundstellen.replaceChildren(
        h("p", { class: "leer" }, `Fundstellen konnten nicht geladen werden. ${e.message}`),
        h("button", { class: "knopf", type: "button", onclick: ladeFundstellen }, "Erneut versuchen"));
    }
  };

  karte.append(
    h("dl", { class: "werte" },
      h("dt", {}, "Name"), h("dd", {}, kunde.name),
      h("dt", {}, "Ort"), h("dd", {}, kunde.ort),
      h("dt", {}, "Ansprechpartner"), h("dd", {}, kunde.ansprechpartner)),
    h("p", { class: "klein gedimmt" }, "🔒 Zugangsdaten stehen nie in der Doku, nur der Verweis auf den Passwortmanager."),
    h("div", { class: "knopfreihe" }, knopf,
      h("button", { class: "knopf", type: "button", onclick: () => oeffneAssistent(t) }, "Kundendoku fragen")),
    doku,
    h("div", { class: "doku-fundstellen" }, h("h4", {}, "Fundstellen zum Ticket"), fundstellen));
  ladeFundstellen();
  return karte;
}
