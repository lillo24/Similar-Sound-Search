"use strict";
const byId = id => document.getElementById(id);
let review, token, documentValue, parent = null, dirty = false, provenance = "local-form";
let storageKey, imported = null;
const players = [];
const ratingLabels = {"not-listened": "Not listened", similar: "Similar type of sound", different: "Different", unsure: "Unsure"};

function status(message, error = false) {
  byId("save-status").textContent = message;
  byId("save-status").className = error ? "error" : "";
}
async function request(path, value) {
  const response = await fetch(path, value === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json", "X-D04-Token": token}, body: JSON.stringify(value)
  });
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "The review request failed");
  return data;
}
function remember() {
  try { localStorage.setItem(storageKey, JSON.stringify({document: documentValue, parent, dirty, provenance})); }
  catch (_) { status("Browser draft storage failed. Save or export your responses to keep them.", true); }
}
function changed() {
  dirty = true;
  remember();
  status("Unsaved draft. Save on this computer or export a JSON file to keep it.");
}
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function player(role, label, availability) {
  const box = node("div", undefined, "player");
  const button = node("button", "Play " + label);
  button.type = "button";
  button.dataset.role = role;
  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.setAttribute("aria-label", role + " · " + label + " · pause and seek");
  audio.setAttribute("controlslist", "noplaybackrate");
  const message = node("p", "", "error");
  message.setAttribute("role", "status");
  const fail = () => {
    button.disabled = true;
    message.textContent = "Unavailable: this saved clip could not be loaded. No substitute is used.";
  };
  audio.addEventListener("play", () => {
    for (const other of players) if (other !== audio) other.pause();
    button.textContent = "Pause " + label;
  });
  audio.addEventListener("pause", () => { button.textContent = "Play " + label; });
  audio.addEventListener("ended", () => { button.textContent = "Play " + label; });
  audio.addEventListener("error", fail);
  button.addEventListener("click", async () => {
    if (!audio.paused) { audio.pause(); return; }
    try { await audio.play(); }
    catch (error) { message.textContent = "Playback failed: " + error.message + ". Try the native play control."; }
  });
  if (availability.available) audio.src = "/media/" + review.record_hash + "/" + role;
  else fail();
  players.push(audio);
  box.append(button, audio, message);
  return box;
}
function bindText(id, target, key) {
  byId(id).value = target[key];
  byId(id).oninput = () => { target[key] = byId(id).value; changed(); };
}
function fillResponses() {
  bindText("section-answer", documentValue.reference, "section");
  bindText("sound-answer", documentValue.reference, "sound");
  bindText("reference-note", documentValue.reference, "note");
  bindText("listener", documentValue, "listener");
  bindText("participation", documentValue, "participation");
  for (const card of review.cards) {
    bindText(card.review_id + "-rating", documentValue.items[card.review_id], "rating");
    bindText(card.review_id + "-note", documentValue.items[card.review_id], "note");
  }
}
function blank() {
  return {schema_version: "d04-feedback-1", review_hash: review.record_hash, listener: "", participation: "pending",
    reference: {section: "not-listened", sound: "", note: ""},
    items: Object.fromEntries(review.cards.map(c => [c.review_id, {rating: "not-listened", note: ""}]))};
}
function download(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + "\n"], {type: "application/json"}));
  const a = document.createElement("a");
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function start() {
  const data = await request("/api/bootstrap");
  review = data.review; token = data.token;
  storageKey = "d04-draft-" + review.record_hash;
  documentValue = data.latest ? data.latest.document : blank();
  parent = data.latest ? data.latest.record_hash : null;
  let restored = false;
  const saved = localStorage.getItem(storageKey);
  if (saved) {
    // Validate drafts through the same review-bound schema as imports and saves.
    try {
      const draft = JSON.parse(saved);
      await request("/api/validate-feedback", draft.document);
      documentValue = draft.document; parent = draft.parent; dirty = draft.dirty;
      provenance = draft.provenance; restored = true;
    } catch (error) { status("Stored draft is invalid; it was retained in browser storage. " + error.message, true); }
  }
  byId("reference-control").append(player("reference", "reference", data.availability.reference));
  byId("reference-player").hidden = false;
  for (const card of review.cards) {
    const section = node("article", undefined, "card");
    section.id = card.review_id;
    section.append(node("p", card.review_id, "eyebrow"), node("h3", card.title), node("p", card.artist, "artist"));
    const controls = node("div", undefined, "players");
    for (const role of ["scored", "context"]) {
      const box = node("div");
      box.append(node("p", (role === "scored" ? "Passage · " : "Unscored context · ") + card[role + "_interval"], "time"),
        player(card.review_id + "-" + role, role === "scored" ? "passage" : "context", data.availability[card.review_id + "-" + role]));
      controls.append(box);
    }
    section.append(controls);
    const select = document.createElement("select");
    select.id = card.review_id + "-rating";
    for (const [value, text] of Object.entries(ratingLabels)) { const option = node("option", text); option.value = value; select.append(option); }
    const label = node("label", "Type of sound (optional)"); label.htmlFor = select.id;
    const note = document.createElement("textarea"); note.rows = 2; note.maxLength = 2000; note.id = card.review_id + "-note";
    const noteLabel = node("label", "Brief reason (optional)"); noteLabel.htmlFor = note.id;
    section.append(label, select, noteLabel, note);
    byId("cards").append(section);
  }
  fillResponses();
  byId("evidence").textContent = JSON.stringify(review, null, 2);
  byId("load-status").textContent = "Saved review ready. Nothing plays automatically.";
  if (restored) status(dirty ? "Unsaved browser draft restored. Save or export it to keep a durable copy." : "Saved response draft restored.");
  else if (data.latest) status("Loaded saved response revision " + data.latest.revision + " from this computer.");
  byId("save").disabled = byId("export").disabled = byId("import").disabled = false;
  byId("save").onclick = async () => {
    byId("save").disabled = true;
    try {
      const sent = structuredClone(documentValue);
      const snapshot = await request("/api/feedback", {document: sent, parent, provenance});
      parent = snapshot.record_hash;
      dirty = JSON.stringify(documentValue) !== JSON.stringify(sent);
      remember();
      status("Saved on this computer as revision " + snapshot.revision + ". " + (dirty ? "Newer edits remain unsaved." : "Export JSON if you want to share it."));
      const c = snapshot.counts;
      byId("human-status").textContent = "Saved self-reported responses: " + c.state + "; " + c.listened_rated + " rated, " + c.similar + " similar, " + c.different + " different, " + c.unsure + " unsure, " + c.unanswered + " unanswered.";
    } catch (error) { status(error.message + " Your current draft is still here.", true); }
    finally { byId("save").disabled = false; }
  };
  byId("export").onclick = async () => {
    try {
      const exported = structuredClone(documentValue);
      await request("/api/validate-feedback", exported);
      download(exported, "D04-feedback-" + review.record_hash.slice(0, 12) + ".json");
      status("JSON download requested. Keep the downloaded file; this page cannot confirm a disk save. " + (dirty ? "Local edits remain unsaved." : "Saved revisions remain on this computer."));
    } catch (error) { status(error.message, true); }
  };
  byId("import").onchange = async () => {
    byId("import-preview").hidden = true; imported = null;
    try {
      if (dirty) throw Error("Save your current edits before importing. No draft was replaced.");
      const file = byId("import").files[0]; if (!file) return;
      if (file.size > 65536) throw Error("Import exceeds 64 KiB");
      const value = JSON.parse(await file.text());
      imported = await request("/api/validate-feedback", value.document || value);
      byId("import-preview").hidden = false;
      status("Import validated for this exact review. Apply it explicitly to change the draft.");
    } catch (error) { status(error.message, true); }
    finally { byId("import").value = ""; }
  };
  byId("apply-import").onclick = () => {
    if (dirty || !imported) { status("Save current edits before applying an import. No draft was replaced.", true); return; }
    documentValue = structuredClone(imported); provenance = "imported-file";
    fillResponses(); changed(); imported = null; byId("import-preview").hidden = true;
  };
}
start().catch(error => { byId("load-status").textContent = "Review unavailable: " + error.message; byId("load-status").className = "error"; });
