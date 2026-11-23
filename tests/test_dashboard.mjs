import assert from "node:assert/strict";
import test from "node:test";

import {
  alter, formatZeit, hatHandlungsbedarf, istDemoZeit, istImSpamfilter, jetzt, nachDringlichkeit, sla, spamOffen, wartezeit,
} from "../frontend/js/hilfen.js";
import { ticketTabelle } from "../frontend/js/ansichten/tickets.js";
import { spamAktionen, zeigeSpam } from "../frontend/js/ansichten/spam.js";
import { aktualisiereAssistent, initAssistent, oeffneAssistent } from "../frontend/js/ansichten/assistent.js";
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
  const spam = { ...ticket({ id: 5, seit: 75 }), spampruefung: { verdaechtig: true } };
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
    addEventListener(name, handler) { this[name] = handler; }
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

test("der Assistent trennt offene Anfragen, Entwürfe und Folgefragen beim Ticketwechsel", async t => {
  testDokument(t);
  const panel = document.createElement("aside");
  document.getElementById = () => panel;
  document.addEventListener = () => {};
  document.body = { classList: { add() {}, remove() {} } };
  let antwortePraxis;
  const aufrufe = [];
  t.mock.method(api, "frageTicket", async (id, frage, vorherige) => {
    aufrufe.push([id, frage, vorherige]);
    if (id === 1021) return new Promise(resolve => { antwortePraxis = resolve; });
    return { antwort: "Datenbankdienst prüfen." };
  });
  t.mock.method(api, "frage", async frage => ({ antwort: `Allgemeine Antwort auf ${frage}` }));
  initAssistent();
  const [, kontext, chat, formular] = panel.children;
  const [eingabe, senden] = formular.children;
  const abschicken = frage => {
    eingabe.value = frage;
    formular.submit({ preventDefault() {} });
  };
  const fertig = () => new Promise(resolve => setImmediate(resolve));
  const praxis = { id: 1021, titel: "Postfach fast voll" };
  const kanzlei = { id: 1017, titel: "Datenbankfehler" };
  oeffneAssistent(praxis);
  abschicken("Postfach prüfen?");
  assert.equal(senden.disabled, true);
  eingabe.value = "Entwurf der Praxis";
  eingabe.input();
  aktualisiereAssistent(kanzlei);
  assert.match(kontext.textContent, /#1017/);
  assert.equal(eingabe.value, "");
  assert.equal(senden.disabled, false);
  abschicken("Alle Arbeitsplätze betroffen.");
  await fertig();
  antwortePraxis({ antwort: "Postfachbelegung prüfen." });
  await fertig();
  assert.match(chat.textContent, /Datenbankdienst/);
  assert.doesNotMatch(chat.textContent, /Postfach/);
  abschicken("Und danach?");
  await fertig();
  assert.deepEqual(aufrufe, [
    [1021, "Postfach prüfen?", undefined],
    [1017, "Alle Arbeitsplätze betroffen.", undefined],
    [1017, "Und danach?", "Alle Arbeitsplätze betroffen."],
  ]);
  aktualisiereAssistent(praxis);
  assert.match(chat.textContent, /Postfachbelegung/);
  assert.equal(eingabe.value, "Entwurf der Praxis");
  aktualisiereAssistent(null);
  assert.equal(eingabe.value, "");
  abschicken("Was ist eine Datenbank?");
  await fertig();
  assert.match(chat.textContent, /Allgemeine Antwort/);
  assert.doesNotMatch(chat.textContent, /Postfachbelegung|Datenbankdienst/);
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

test("Eingangsfilter sortiert vor der KI-Bewertung, Freigaben und Abschlüsse haben Vorrang", () => {
  const offen = { ...ticket(), spampruefung: { verdaechtig: true } };
  const freigegeben = { ...offen, spam_entscheidung: "kein_spam", ki: { spam: true } };
  const bestaetigt = { ...offen, spam_entscheidung: "spam", status: "geschlossen" };
  const alt = { ...offen, ki: { spam: true }, spampruefung: { verdaechtig: false } };
  assert.equal(spamOffen(offen), true);
  assert.equal(hatHandlungsbedarf(offen), false);
  assert.equal(sla(offen, jetztImTest).zustand, "keine");
  for (const frei of [freigegeben, alt]) {
    assert.equal(spamOffen(frei), false);
    assert.equal(hatHandlungsbedarf(frei), true);
    assert.equal(sla(frei, jetztImTest).zustand, "gelb");
  }
  assert.equal(spamOffen(bestaetigt), false);
  const archivierterVerdacht = { ...offen, status: "geschlossen" };
  assert.equal(istImSpamfilter(archivierterVerdacht), true);
  assert.equal(spamOffen(archivierterVerdacht), false);
});

test("Spam-Prüfung zeigt nur offene Eingangsverdachte und den tatsächlichen Prüfgrund", (t) => {
  testDokument(t);
  browserGlobal(t, "location", { search: "" });
  const vorher = zustand.tickets;
  t.after(() => { zustand.tickets = vorher; });
  const filter = { verdaechtig: true, begruendung: "Unaufgeforderte Verkaufsnachricht." };
  zustand.tickets = [
    { ...ticket({ id: 11 }), titel: "Werbesendung", spampruefung: filter },
    { ...ticket({ id: 12 }), titel: "Monitor anfordern", ki: { spam: true }, spampruefung: { verdaechtig: false } },
    { ...ticket({ id: 13 }), titel: "Freigegeben", spam_entscheidung: "kein_spam", spampruefung: filter },
    { ...ticket({ id: 14, status: "geschlossen" }), titel: "Bestätigte Werbung", spam_entscheidung: "spam", spampruefung: filter },
    { ...ticket({ id: 15 }), titel: "Manuelle Korrektur", spam_entscheidung: "kein_spam", spampruefung: { verdaechtig: false } },
  ];
  const ziel = document.createElement("main");
  zeigeSpam(ziel);
  const [kopf, queue, freigegeben] = ziel.children;
  assert.match(kopf.textContent, /Bestätigt: 1/);
  assert.match(queue.textContent, /#11 Werbesendung/);
  assert.match(queue.textContent, /Unaufgeforderte Verkaufsnachricht/);
  assert.doesNotMatch(queue.textContent, /#12|#13|#14|#15/);
  assert.equal(freigegeben.tag, "details");
  assert.match(freigegeben.textContent, /Vom Support freigegeben \(1\)/);
  assert.match(freigegeben.textContent, /#13 Freigegeben/);
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
  const alt = { ...ticket(), spampruefung: { verdaechtig: true } };
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

test("Eingang erneut prüfen gibt die manuelle Entscheidung gezielt an den Filter zurück", async (t) => {
  testDokument(t);
  t.mock.method(globalThis, "setTimeout", () => 0);
  const vorher = zustand.tickets;
  t.after(() => { zustand.tickets = vorher; });
  const frei = { ...ticket(), spam_entscheidung: "kein_spam", spampruefung: { verdaechtig: true, art: "werbung" } };
  const erneut = { ...frei, spam_entscheidung: null };
  zustand.tickets = [frei];
  const patch = t.mock.method(api, "ticketAendern", async () => erneut);
  const aktion = spamAktionen(frei).children.find((k) => k.textContent === "Eingang erneut prüfen");
  await aktion.click();
  assert.deepEqual(patch.mock.calls[0].arguments, [frei.id, {
    spam_entscheidung: null, erwartete_spam_entscheidung: "kein_spam", erwarteter_status: "neu",
  }]);
  assert.equal(spamOffen(zustand.tickets[0]), true);
  assert.match(document.getElementById("meldungen").textContent, /nach Spam \/ Werbung verschoben/);
});
