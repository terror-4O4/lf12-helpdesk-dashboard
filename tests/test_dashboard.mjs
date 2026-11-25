import assert from "node:assert/strict";
import test from "node:test";

import {
  alter, formatZeit, hatHandlungsbedarf, istDemoZeit, istImSpamfilter, jetzt, markdown, nachDringlichkeit, sla, spamOffen, ticketPrioBadge, wartezeit,
} from "../frontend/js/hilfen.js";
import { ticketTabelle } from "../frontend/js/ansichten/tickets.js";
import { zeigeTicket } from "../frontend/js/ansichten/ticket.js";
import { spamAktionen, zeigeSpam } from "../frontend/js/ansichten/spam.js";
import { api, ApiFehler } from "../frontend/js/api.js";
import { ladeDaten, ticketErsetzen, zustand } from "../frontend/js/zustand.js";

const jetztImTest = new Date("2026-11-19T11:30:00Z");
const davor = (minuten) => new Date(jetztImTest.getTime() - minuten * 60000).toISOString();

function ticket({ id = 1, status = "neu", prioritaet = "sehr_hoch", seit = 15, alterInMinuten = 120 } = {}) {
  return {
    id, status, prioritaet, titel: "Beispielticket", erstellt_am: davor(alterInMinuten),
    statushistorie: [{ status, seit: davor(seit) }],
  };
}

function browserGlobal(t, name, wert) {
  const vorher = Object.getOwnPropertyDescriptor(globalThis, name);
  Object.defineProperty(globalThis, name, { value: wert, configurable: true, writable: true });
  t.after(() => {
    if (vorher) Object.defineProperty(globalThis, name, vorher);
    else delete globalThis[name];
  });
}

test("Halbzeit und Reaktionsfrist haben für jede Priorität feste Grenzen", () => {
  const fristen = { sehr_hoch: 30, hoch: 120, mittel: 480, niedrig: 1440, unbewertet: 120 };
  for (const [prioritaet, frist] of Object.entries(fristen)) {
    const farbe = (seit) => sla(ticket({ prioritaet, seit }), jetztImTest).zustand;
    assert.equal(farbe(frist / 2 - 1 / 60), "gruen", prioritaet);
    assert.equal(farbe(frist / 2), "gelb", prioritaet);
    assert.equal(farbe(frist - 1 / 60), "gelb", prioritaet);
    assert.equal(farbe(frist), "rot", prioritaet);
    assert.equal(farbe(frist + 1 / 60), "rot", prioritaet);
  }
  assert.equal(sla(ticket({ seit: 30 }), jetztImTest).text, "Reaktionsfrist erreicht");
});

test("die Wartezeit beginnt beim neuen Status und das Ticketalter bleibt erhalten", () => {
  const antwort = ticket({ status: "antwort_erhalten", seit: 7, alterInMinuten: 120 });
  antwort.statushistorie.unshift({ status: "warten_auf_kunde", seit: davor(45) });
  assert.deepEqual(wartezeit(antwort, jetztImTest), { auf: "Support", minuten: 7 });
  assert.equal(alter(antwort.erstellt_am, jetztImTest), "vor 2 Std.");
  assert.equal(sla(antwort, jetztImTest).zustand, "gruen");

  const wartet = ticket({ status: "warten_auf_kunde", seit: 35 });
  assert.deepEqual(wartezeit(wartet, jetztImTest), { auf: "Kunde", minuten: 35 });
  assert.equal(sla(wartet, jetztImTest).zustand, "pausiert");
  for (const status of ["in_bearbeitung", "geparkt", "geschlossen"]) {
    assert.equal(wartezeit(ticket({ status }), jetztImTest), null);
  }
  assert.equal(sla(ticket({ status: "geschlossen" }), jetztImTest).zustand, "keine");
});

test("Neu und Antwort erhalten haben Vorrang, bei Gleichstand entscheidet das tatsächliche Alter", () => {
  const spaeterErstellt = ticket({ id: 1, seit: 15, alterInMinuten: 120 });
  const frueherErstellt = ticket({ id: 2, seit: 15, alterInMinuten: 140 });
  const wartend = ticket({ id: 3, status: "warten_auf_kunde", seit: 80 });
  const ueberfaellig = ticket({ id: 4, status: "antwort_erhalten", seit: 45 });
  const spam = { ...ticket({ id: 5, seit: 75 }), ki: { spam: true } };
  assert.equal(hatHandlungsbedarf(spam), false);
  assert.equal(hatHandlungsbedarf({ ...spam, spam_entscheidung: "kein_spam" }), true);

  const visuell = [wartend, spaeterErstellt, frueherErstellt, ueberfaellig, spam]
    .sort((a, b) => nachDringlichkeit(a, b, jetztImTest));
  assert.deepEqual(visuell.filter(hatHandlungsbedarf).map((t) => t.id), [4, 2, 1]);
  assert.equal(visuell[0].id, 4);
  assert.equal(visuell[2].id, 1);
});

test("ungültige Zeitstempel und eine Demo-Zeit vor Erstellung bleiben darstellbar", (t) => {
  browserGlobal(t, "location", { search: "?jetzt=ungueltig" });
  assert.equal(istDemoZeit(), false);
  assert.equal(formatZeit("ungueltig"), "");
  assert.equal(sla({ ...ticket(), erstellt_am: "kaputt", statushistorie: [] }, jetztImTest).zustand, "keine");
  assert.deepEqual(wartezeit(ticket({ seit: -20 }), jetztImTest), { auf: "Support", minuten: 0 });
  globalThis.location.search = "?jetzt=2026-11-19T11%3A30%3A00Z";
  assert.equal(istDemoZeit(), true);
  assert.deepEqual(jetzt(), jetztImTest);
});

function testDokument(t) {
  class Element {
    constructor(tag, text = "") {
      this.tag = tag;
      this.text = text;
      this.children = [];
      this.attributes = {};
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.text = ""; this.children = children; }
    focus() {}
    setAttribute(name, value) { this.attributes[name] = value; }
    getAttribute(name) { return this.attributes[name]; }
    get childNodes() { return this.children; }
    addEventListener(name, handler) { this[name] = handler; }
    get tagName() { return this.tag.toUpperCase(); }
    get textContent() { return this.text + this.children.map((child) => child.textContent).join(""); }
    set textContent(text) { this.text = text; this.children = []; }
  }
  browserGlobal(t, "Node", Element);
  const meldungen = new Element("div");
  browserGlobal(t, "document", {
    createElement: (tag) => new Element(tag),
    createDocumentFragment: () => new Element("#fragment"),
    createTextNode: (text) => new Element("#text", text),
    getElementById: (id) => id === "meldungen" ? meldungen : null,
  });
}

test("Beratungspunkte erscheinen als Liste und Modellprioritäten tragen eine lesbare Kennzeichnung", t => {
  testDokument(t);
  const [liste] = markdown("- **Prüfe** den Gerätestatus.\n- Notiere die angezeigte Meldung.").children;
  assert.equal(liste.tag, "ul");
  assert.deepEqual(liste.children.map(el => el.tag), ["li", "li"]);
  const basis = { prioritaet: "hoch", prioritaet_quelle: "ki" };
  const bewertet = (modus, t = basis) => ticketPrioBadge({ ...t, ki: { modus } });
  assert.equal(bewertet("llama").textContent, "Hoch ✦");
  assert.match(bewertet("llama").attributes.title, /Sprachmodell/);
  assert.equal(bewertet("mock").textContent, "Hoch");
  assert.match(bewertet("mock").attributes.title, /Demo/);
  assert.equal(bewertet("llama", { ...basis, prioritaet_quelle: "manuell" }).attributes.title, "Von Hand gesetzt");
  assert.equal(ticketPrioBadge(basis).textContent, "Hoch ✦");
});

test("in der Ticketliste stehen Alter und Wartezeit in getrennten Spalten", (t) => {
  testDokument(t);
  const wrapper = ticketTabelle([ticket({ status: "warten_auf_kunde", seit: 35 })], {
    kompakt: true, bezugszeit: jetztImTest,
  });
  const [thead, tbody] = wrapper.children[0].children;
  assert.deepEqual(thead.children[0].children.slice(-2).map((el) => el.textContent), ["Ticketalter", "Wartezeit"]);
  const [alterZelle, wartezeitZelle] = tbody.children[0].children.slice(-2);
  assert.equal(alterZelle.textContent, "vor 2 Std.");
  assert.equal(wartezeitZelle.textContent, "35 Min.");
  assert.equal(wartezeitZelle.attributes.title, "Wartezeit auf Kunde");
});

test("Modellverdacht steuert die Spamprüfung, Freigaben und Abschlüsse haben Vorrang", () => {
  const offen = { ...ticket(), ki: { spam: true } };
  const freigegeben = { ...offen, spam_entscheidung: "kein_spam", ki: { spam: true } };
  const bestaetigt = { ...offen, spam_entscheidung: "spam", status: "geschlossen" };
  const regelhinweis = { ...ticket(), regelhinweise: ["Werbesprache erkannt."], spampruefung: { verdaechtig: true } };
  assert.equal(spamOffen(offen), true);
  assert.equal(hatHandlungsbedarf(offen), false);
  assert.equal(sla(offen, jetztImTest).zustand, "keine");
  for (const frei of [freigegeben, regelhinweis, { ...regelhinweis, ki: { spam: false } }]) {
    assert.equal(spamOffen(frei), false);
    assert.equal(hatHandlungsbedarf(frei), true);
    assert.equal(sla(frei, jetztImTest).zustand, "gelb");
  }
  assert.equal(spamOffen(bestaetigt), false);
  const archivierterVerdacht = { ...offen, status: "geschlossen" };
  assert.equal(istImSpamfilter(archivierterVerdacht), true);
  assert.equal(spamOffen(archivierterVerdacht), false);
});

test("Spam-Prüfung zeigt offene Modellverdachte und deren Modellbegründung", (t) => {
  testDokument(t);
  browserGlobal(t, "location", { search: "" });
  const vorher = zustand.tickets;
  t.after(() => { zustand.tickets = vorher; });
  const ki = { spam: true, begruendung: "Unaufgeforderte Verkaufsnachricht." };
  zustand.tickets = [
    { ...ticket({ id: 11 }), titel: "Werbesendung", ki },
    { ...ticket({ id: 12 }), titel: "Monitor anfordern", ki: { spam: false }, regelhinweise: ["Werbehinweis"] },
    { ...ticket({ id: 13 }), titel: "Freigegeben", spam_entscheidung: "kein_spam", ki },
    { ...ticket({ id: 14, status: "geschlossen" }), titel: "Bestätigte Werbung", spam_entscheidung: "spam", ki },
    { ...ticket({ id: 15 }), titel: "Manuelle Korrektur", spam_entscheidung: "kein_spam", ki: { spam: false } },
  ];
  const ziel = document.createElement("main");
  zeigeSpam(ziel);
  const [kopf, queue, freigegeben] = ziel.children;
  assert.match(kopf.textContent, /Bestätigt: 1/);
  assert.match(queue.textContent, /#11 Werbesendung/);
  assert.match(queue.textContent, /Unaufgeforderte Verkaufsnachricht/);
  assert.match(queue.textContent, /✦ Spam-Verdacht/);
  assert.doesNotMatch(queue.textContent, /#12|#13|#14|#15/);
  assert.equal(freigegeben.tag, "details");
  assert.match(freigegeben.textContent, /Vom Support freigegeben \(1\)/);
  assert.match(freigegeben.textContent, /#13 Freigegeben/);
});

test("Detailansicht hält Modellwerte, Regelhinweis und manuelle Entscheidungen auseinander", t => {
  testDokument(t);
  browserGlobal(t, "location", { search: "" });
  const vorher = zustand.tickets;
  t.after(() => { zustand.tickets = vorher; });
  const fall = {
    ...ticket(), prioritaet_quelle: "manuell", ki: {
      modus: "llama", prioritaet: "mittel", kategorie: "Software", spam: true, begruendung: "Modellbegründung",
    }, regelhinweise: ["Separater Hinweis"],
  };
  for (const entscheidung of [null, "kein_spam", "spam"]) {
    zustand.tickets = [{ ...fall, spam_entscheidung: entscheidung }];
    const ziel = document.createElement("main");
    zeigeTicket(ziel, { teile: [String(fall.id)] });
    const karten = ziel.children[2].children[1].children;
    const analyse = karten.find(el => el.attributes["aria-labelledby"] === "t-ki");
    assert.match(analyse.textContent, /✦ KI-EinschätzungPrioritätMittel ✦KategorieSoftwareSpamJa/);
    assert.match(analyse.textContent, /„Sehr hoch“/);
    assert.match(analyse.textContent, /Modellbegründung/);
    assert.doesNotMatch(analyse.textContent, /Separater Hinweis/);
    assert.equal(karten.find(el => el.textContent === "RegelhinweiseSeparater Hinweis").className, "karte");
    if (entscheidung === "kein_spam") {
      assert.doesNotMatch(ziel.children[1].textContent, /Spam-Verdacht/);
      assert.match(ziel.children[1].textContent, /Sehr hoch/);
    } else if (entscheidung === null) {
      assert.match(ziel.children[1].textContent, /✦ Spam-Verdacht/);
      assert.match(analyse.textContent, /✦ Neu bewerten/);
    } else {
      assert.match(ziel.children[1].textContent, /Spam bestätigt/);
      assert.doesNotMatch(analyse.textContent, /Neu bewerten/);
    }
  }
});

test("eine Hintergrundabfrage darf eine jüngere Ticketänderung nicht überschreiben", async (t) => {
  let stelleTicketsZu;
  const response = (inhalt) => ({ ok: true, json: async () => inhalt });
  t.mock.method(globalThis, "fetch", (adresse) => {
    if (adresse === "/api/tickets") return new Promise((resolve) => { stelleTicketsZu = resolve; });
    return Promise.resolve(response([]));
  });
  const vorher = ticket();
  const nachher = { ...vorher, status: "in_bearbeitung" };
  zustand.tickets = [vorher];
  const abfrage = ladeDaten();
  ticketErsetzen(nachher);
  stelleTicketsZu(response([vorher]));
  await abfrage;
  assert.equal(zustand.tickets[0].status, "in_bearbeitung");
});

test("eine überholte Spam-Freigabe lädt die aktuelle Entscheidung, auch wenn das alte Ticket kein Entscheidungsfeld hat", async (t) => {
  testDokument(t);
  t.mock.method(globalThis, "setTimeout", () => 0);
  const vorher = zustand.tickets;
  t.after(() => { zustand.tickets = vorher; });
  const alt = { ...ticket(), ki: { spam: true } };
  const aktuell = { ...alt, status: "geschlossen", spam_entscheidung: "spam" };
  zustand.tickets = [alt];
  const patch = t.mock.method(api, "ticketAendern", async () => { throw new ApiFehler("Überholt", 409); });
  const abruf = t.mock.method(api, "ticket", async () => aktuell);
  const freigabe = spamAktionen(alt).children.find((k) => k.textContent === "Kein Spam");
  await freigabe.click();
  assert.deepEqual(patch.mock.calls[0].arguments, [alt.id, {
    spam_entscheidung: "kein_spam", erwartete_spam_entscheidung: null, erwarteter_status: "neu",
  }]);
  assert.deepEqual(abruf.mock.calls[0].arguments, [alt.id]);
  assert.deepEqual(zustand.tickets, [aktuell]);
  assert.match(document.getElementById("meldungen").textContent, /inzwischen geändert/);
  assert.equal(spamOffen(zustand.tickets[0]), false);
});

test("Freigabe aufheben aktiviert den gespeicherten Modellverdacht wieder", async (t) => {
  testDokument(t);
  t.mock.method(globalThis, "setTimeout", () => 0);
  const vorher = zustand.tickets;
  t.after(() => { zustand.tickets = vorher; });
  const frei = { ...ticket(), spam_entscheidung: "kein_spam", ki: { spam: true } };
  const erneut = { ...frei, spam_entscheidung: null };
  zustand.tickets = [frei];
  const patch = t.mock.method(api, "ticketAendern", async () => erneut);
  const aktion = spamAktionen(frei).children.find((k) => k.textContent === "Freigabe aufheben");
  await aktion.click();
  assert.deepEqual(patch.mock.calls[0].arguments, [frei.id, {
    spam_entscheidung: null, erwartete_spam_entscheidung: "kein_spam", erwarteter_status: "neu",
  }]);
  assert.equal(spamOffen(zustand.tickets[0]), true);
  assert.match(document.getElementById("meldungen").textContent, /nach Spam \/ Werbung verschoben/);
});
