// Ticket anlegen, Eingangsprüfung berücksichtigen und auf Wunsch bewerten.

import { api } from "../api.js";
import { h, spamOffen } from "../hilfen.js";
import { meldung, ticketErsetzen, zustand } from "../zustand.js";

export function oeffneNeuesTicket() {
  const kunde = h("select", { id: "n-kunde", required: true },
    h("option", { value: "", disabled: true, selected: true }, "Kunde wählen"),
    zustand.kunden.map((k) => h("option", { value: k.kunde }, k.name)),
    h("option", { value: "_ohne" }, "Unbekannter Absender"));
  const titel = h("input", { id: "n-titel", type: "text", required: true, maxlength: 200, placeholder: "Kurze Zusammenfassung" });
  const text = h("textarea", {
    id: "n-text", required: true, rows: 8, maxlength: 5000,
    placeholder: "Mail hier einfügen oder Anruf kurz notieren …",
  });
  const bewerten = h("input", { type: "checkbox", checked: true });
  const anlegen = h("button", { class: "knopf knopf-haupt", type: "submit" }, "Ticket anlegen");

  const dialog = h("dialog", { class: "dialog", "aria-labelledby": "n-ueberschrift" },
    h("form", { class: "formular", method: "dialog" },
      h("div", { class: "dialog-kopf" },
        h("h2", { id: "n-ueberschrift" }, "Neues Ticket"),
        h("button", { class: "knopf-klein", type: "button", "aria-label": "Schließen", onclick: () => dialog.close() }, "×")),
      h("label", { for: "n-kunde" }, "Kunde", kunde),
      h("label", { for: "n-titel" }, "Betreff", titel),
      h("label", { for: "n-text" }, "Nachricht", text),
      h("label", { class: "inline" }, bewerten, " ", h("span", { class: "ki-marke" }, "✦ KI-Bewertung"),
        " mit Spam-Prüfung starten und für Supporttickets ähnliche Fälle suchen"),
      h("div", { class: "knopfreihe" },
        anlegen,
        h("button", { class: "knopf", type: "button", onclick: () => dialog.close() }, "Abbrechen"))));

  dialog.querySelector("form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    anlegen.disabled = true;
    anlegen.textContent = "Lege an …";
    try {
      let t = await api.ticketAnlegen({
        kunde: kunde.value === "_ohne" ? null : kunde.value,
        titel: titel.value.trim(),
        beschreibung: text.value.trim(),
      });
      ticketErsetzen(t);
      if (bewerten.checked) {
        anlegen.textContent = "KI bewertet …";
        try {
          await api.analysieren(t.id);
          t = await api.ticket(t.id);
          ticketErsetzen(t);
          if (!spamOffen(t)) {
            anlegen.textContent = "Suche ähnliche Fälle …";
            await api.loesungsvorschlag(t.id);
          }
        } catch (e) {
          meldung(`Angelegt, aber KI fehlgeschlagen: ${e.message}`, "fehler");
        }
      }
      dialog.close();
      meldung(spamOffen(t) ? `Ticket #${t.id} liegt unter Spam / Werbung.` : `Ticket #${t.id} angelegt`, "erfolg");
      location.hash = `#/ticket/${t.id}`;
    } catch (e) {
      meldung(e.message, "fehler");
      anlegen.disabled = false;
      anlegen.textContent = "Ticket anlegen";
    }
  });

  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
  kunde.focus();
}
