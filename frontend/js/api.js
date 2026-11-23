// Alle Aufrufe ans Backend. Das Dashboard wird vom Backend selbst ausgeliefert,
// daher reichen relative Pfade (/api/...). Es gibt keine Anfragen nach extern.

export class ApiFehler extends Error {
  constructor(nachricht, code) {
    super(nachricht);
    this.code = code;
  }
}

async function anfrage(methode, pfad, daten) {
  const optionen = { method: methode, headers: {} };
  if (daten !== undefined) {
    optionen.headers["Content-Type"] = "application/json";
    optionen.body = JSON.stringify(daten);
  }

  let antwort;
  try {
    antwort = await fetch(pfad, optionen);
  } catch {
    throw new ApiFehler("Backend nicht erreichbar. Läuft start-backend?", 0);
  }

  let inhalt = null;
  try {
    inhalt = await antwort.json();
  } catch {
    // keine JSON-Antwort, z. B. bei 405 ohne Inhalt
  }

  if (!antwort.ok) {
    if (antwort.status === 405) {
      throw new ApiFehler("Diese Funktion kennt das Backend noch nicht (Backend aktualisieren).", 405);
    }
    throw new ApiFehler(fehlertext(inhalt) || `Fehler ${antwort.status}`, antwort.status);
  }
  return inhalt;
}

// FastAPI liefert Fehler als {"detail": "..."} oder bei Prüffehlern als Liste
function fehlertext(inhalt) {
  if (!inhalt || inhalt.detail === undefined) return "";
  if (typeof inhalt.detail === "string") return inhalt.detail;
  if (Array.isArray(inhalt.detail)) return inhalt.detail.map((d) => d.msg).join(", ");
  return "";
}

export const api = {
  status: () => anfrage("GET", "/api/status?modelldetails=true"),
  tickets: () => anfrage("GET", "/api/tickets"),
  ticket: (id) => anfrage("GET", `/api/tickets/${id}`),
  ticketAnlegen: (daten) => anfrage("POST", "/api/tickets", daten),
  ticketAendern: (id, aenderung) => anfrage("PATCH", `/api/tickets/${id}`, aenderung),
  analysieren: (id) => anfrage("POST", `/api/tickets/${id}/analyse`),
  loesungsvorschlag: (id) => anfrage("POST", `/api/tickets/${id}/loesungsvorschlag`),
  kunden: () => anfrage("GET", "/api/kunden"),
  kundendoku: (kunde) => anfrage("GET", `/api/kunden/${encodeURIComponent(kunde)}/doku`),
  ticketDoku: (id) => anfrage("GET", `/api/tickets/${id}/doku`),
  frageTicket: (id, frage, vorherige_frage) =>
    anfrage("POST", `/api/tickets/${id}/frage`, { frage, vorherige_frage }),
  frageWikipedia: (frage) => anfrage("POST", "/api/wissen/wikipedia", { frage }),
  frageKundendoku: (kunde, frage) =>
    anfrage("POST", `/api/kunden/${encodeURIComponent(kunde)}/doku/suche`, { frage }),
  frage: (text) => anfrage("POST", "/api/ki/frage", { frage: text }),
};
