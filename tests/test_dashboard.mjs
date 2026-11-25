import assert from "node:assert/strict";
import test from "node:test";

import {
  alter, formatZeit, hatHandlungsbedarf, istDemoZeit, jetzt, nachDringlichkeit, sla, wartezeit,
} from "../frontend/js/hilfen.js";
import { ticketTabelle } from "../frontend/js/ansichten/tickets.js";
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

test("in der Ticketliste stehen Alter und Wartezeit in getrennten Spalten", (t) => {
  class Element {
    constructor(tag, text = "") {
      this.tag = tag;
      this.text = text;
      this.children = [];
      this.attributes = {};
    }
    append(child) { this.children.push(child); }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener() {}
    get textContent() { return this.text + this.children.map((child) => child.textContent).join(""); }
  }
  browserGlobal(t, "Node", Element);
  browserGlobal(t, "document", {
    createElement: (tag) => new Element(tag),
    createTextNode: (text) => new Element("#text", text),
  });
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
