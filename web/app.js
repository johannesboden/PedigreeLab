const canvas = document.getElementById("canvas");
const linksLayer = document.getElementById("links");
const nodesLayer = document.getElementById("nodes");
const form = document.getElementById("personForm");
const statusEl = document.getElementById("status");
const errorsEl = document.getElementById("errors");
const filePathEl = document.getElementById("filePath");
const autosaveStateEl = document.getElementById("autosaveState");
const deletePersonBtn = document.getElementById("deletePersonBtn");
const personIdsEl = document.getElementById("personIds");
const personPanel = document.getElementById("personPanel");
const legacyPanel = document.getElementById("legacyPanel");
const legacyTool = document.getElementById("legacyTool");
const legacyNote = document.getElementById("legacyNote");
const legacyCellInfo = document.getElementById("legacyCellInfo");
const applyLegacyNoteBtn = document.getElementById("applyLegacyNoteBtn");

let pedigree = { people: [], comments: [], errors: [] };
let selectedId = null;
let selectedCell = null;
let drag = null;
let draggedNode = null;
let saveTimer = null;
let dirty = false;

const fields = {
  individual_id: document.getElementById("individualId"),
  family_id: document.getElementById("familyId"),
  sex: document.getElementById("sex"),
  phenotype: document.getElementById("phenotype"),
  paternal_id: document.getElementById("paternalId"),
  maternal_id: document.getElementById("maternalId"),
  x: document.getElementById("posX"),
  y: document.getElementById("posY"),
};

document.getElementById("addPersonBtn").addEventListener("click", addPerson);
document.getElementById("addParentsBtn").addEventListener("click", addParents);
document.getElementById("addChildBtn").addEventListener("click", addChild);
deletePersonBtn.addEventListener("click", deleteSelectedPerson);
document.getElementById("layoutBtn").addEventListener("click", autoLayout);
document.getElementById("exportSvgBtn").addEventListener("click", exportSvg);
document.getElementById("saveBtn").addEventListener("click", () => savePedigree({ manual: true }));
form.addEventListener("submit", applyForm);
form.addEventListener("change", applyFormChange);
applyLegacyNoteBtn.addEventListener("click", applyLegacyNote);
window.addEventListener("beforeunload", (event) => {
  if (!dirty) return;
  event.preventDefault();
  event.returnValue = "";
});

loadPedigree();

async function loadPedigree() {
  const response = await fetch("/api/pedigree");
  pedigree = await response.json();
  selectedId = pedigree.people?.[0]?.individual_id ?? null;
  render();
  setStatus("Geladen");
  setAutosaveState("saved", "Automatisch gespeichert");
}

async function savePedigree(options = {}) {
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }
  setAutosaveState("saving", options.manual ? "Sichert..." : "Speichert automatisch...");
  const response = await fetch("/api/pedigree", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(pedigree),
  });
  const payload = await response.json();
  if (!response.ok) {
    setStatus(payload.error || "Speichern fehlgeschlagen");
    setAutosaveState("error", "Speichern fehlgeschlagen");
    return;
  }
  pedigree = payload;
  dirty = false;
  render();
  const time = new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  setStatus(options.manual ? "Manuell gesichert" : "Automatisch gesichert");
  setAutosaveState("saved", `Gesichert ${time}`);
}

async function autoLayout() {
  const response = await fetch("/api/layout");
  if (isLegacyMode()) {
    setStatus("Layout ist im Rastermodus manuell");
    return;
  }
  pedigree = await response.json();
  render();
  setStatus("Layout aktualisiert");
  markDirty("Layout geändert");
}

function addPerson() {
  if (isLegacyMode()) {
    setStatus("Im Rastermodus bitte ein Symbol-Werkzeug wählen");
    return;
  }
  const familyId = selectedPerson()?.family_id || "FAM1";
  const newId = nextId("P");
  pedigree.people.push({
    family_id: familyId,
    individual_id: newId,
    paternal_id: "0",
    maternal_id: "0",
    sex: "0",
    phenotype: "0",
    x: 120,
    y: 120,
    extra_columns: [],
  });
  selectedId = newId;
  normalizeStructuredSpacing();
  render();
  setStatus("Person angelegt");
  markDirty("Neue Person");
}

function addParents() {
  if (isLegacyMode()) return;
  const child = selectedPerson();
  if (!child) {
    setStatus("Erst eine Person auswählen");
    return;
  }
  const fatherId = child.paternal_id !== "0" ? child.paternal_id : nextId("V");
  const motherId = child.maternal_id !== "0" ? child.maternal_id : nextId("M");
  if (!findPerson(fatherId)) {
    pedigree.people.push(makePerson(fatherId, child.family_id, "1", child.x - 80, child.y - 150));
  }
  if (!findPerson(motherId)) {
    pedigree.people.push(makePerson(motherId, child.family_id, "2", child.x + 80, child.y - 150));
  }
  child.paternal_id = fatherId;
  child.maternal_id = motherId;
  selectedId = child.individual_id;
  normalizeStructuredSpacing();
  render();
  setStatus("Eltern angelegt");
  markDirty("Eltern angelegt");
}

function addChild() {
  if (isLegacyMode()) return;
  const parent = selectedPerson();
  if (!parent) {
    setStatus("Erst eine Person auswählen");
    return;
  }
  const childId = nextId("K");
  const child = makePerson(childId, parent.family_id, "0", parent.x, parent.y + 150);
  if (parent.sex === "1") {
    child.paternal_id = parent.individual_id;
  } else if (parent.sex === "2") {
    child.maternal_id = parent.individual_id;
  } else {
    child.paternal_id = parent.individual_id;
  }
  pedigree.people.push(child);
  selectedId = childId;
  normalizeStructuredSpacing();
  render();
  setStatus("Kind angelegt");
  markDirty("Kind angelegt");
}

function deleteSelectedPerson() {
  if (isLegacyMode()) {
    deleteSelectedCell();
    return;
  }
  const person = selectedPerson();
  if (!person) return;
  const confirmed = window.confirm(`${person.individual_id} wirklich aus dem Stammbaum entfernen?`);
  if (!confirmed) return;
  pedigree.people = pedigree.people.filter((item) => item.individual_id !== person.individual_id);
  for (const other of pedigree.people) {
    if (other.paternal_id === person.individual_id) other.paternal_id = "0";
    if (other.maternal_id === person.individual_id) other.maternal_id = "0";
  }
  selectedId = pedigree.people[0]?.individual_id ?? null;
  render();
  setStatus("Person entfernt");
  markDirty("Person entfernt");
}

function makePerson(id, familyId, sex, x, y) {
  return {
    family_id: familyId || "FAM1",
    individual_id: id,
    paternal_id: "0",
    maternal_id: "0",
    sex,
    phenotype: "0",
    x,
    y,
    extra_columns: [],
  };
}

function normalizeStructuredSpacing() {
  const rows = new Map();
  for (const person of pedigree.people) {
    const rowKey = Math.round((person.y || 120) / 25) * 25;
    if (!rows.has(rowKey)) rows.set(rowKey, []);
    rows.get(rowKey).push(person);
  }
  for (const people of rows.values()) {
    people.sort((left, right) => (left.x || 0) - (right.x || 0));
    for (let index = 1; index < people.length; index += 1) {
      const previous = people[index - 1];
      const current = people[index];
      current.x = Math.max(current.x || 120, (previous.x || 120) + 135);
    }
  }
}

function applyForm(event) {
  event.preventDefault();
  const person = selectedPerson();
  if (!person) return;
  const oldId = person.individual_id;
  const newId = fields.individual_id.value.trim() || nextId("P");
  if (newId !== oldId && findPerson(newId)) {
    setStatus("ID existiert bereits");
    return;
  }

  person.individual_id = newId;
  person.family_id = fields.family_id.value.trim() || "FAM1";
  person.sex = fields.sex.value || "0";
  person.phenotype = fields.phenotype.value.trim() || "0";
  person.paternal_id = fields.paternal_id.value.trim() || "0";
  person.maternal_id = fields.maternal_id.value.trim() || "0";
  person.x = Number(fields.x.value || 0);
  person.y = Number(fields.y.value || 0);

  for (const other of pedigree.people) {
    if (other.paternal_id === oldId) other.paternal_id = newId;
    if (other.maternal_id === oldId) other.maternal_id = newId;
  }
  selectedId = newId;
  render();
  setStatus("Änderungen übernommen");
  markDirty("Person geändert");
}

function applyFormChange() {
  if (applyFormValues()) {
    render();
    setStatus("Änderung übernommen");
    markDirty("Formular geändert");
  }
}

function applyFormValues() {
  const person = selectedPerson();
  if (!person) return false;
  const oldId = person.individual_id;
  const newId = fields.individual_id.value.trim() || oldId || nextId("P");
  if (newId !== oldId && findPerson(newId)) return false;

  person.individual_id = newId;
  person.family_id = fields.family_id.value.trim() || "FAM1";
  person.sex = fields.sex.value || "0";
  person.phenotype = fields.phenotype.value.trim() || "0";
  person.paternal_id = fields.paternal_id.value.trim() || "0";
  person.maternal_id = fields.maternal_id.value.trim() || "0";
  person.x = Number(fields.x.value || 0);
  person.y = Number(fields.y.value || 0);

  for (const other of pedigree.people) {
    if (other.paternal_id === oldId) other.paternal_id = newId;
    if (other.maternal_id === oldId) other.maternal_id = newId;
  }
  selectedId = newId;
  return true;
}

function render() {
  filePathEl.textContent = pedigree.source_path || "";
  linksLayer.replaceChildren();
  nodesLayer.replaceChildren();
  if (isLegacyMode()) {
    renderLegacy();
    return;
  }
  personPanel.hidden = false;
  legacyPanel.hidden = true;
  setToolbarForLegacy(false);

  const people = new Map(pedigree.people.map((person) => [person.individual_id, person]));
  for (const person of pedigree.people) {
    if (person.x == null || person.y == null) {
      person.x = 120;
      person.y = 120;
    }
  }

  for (const child of pedigree.people) {
    const father = people.get(child.paternal_id);
    const mother = people.get(child.maternal_id);
    if (father && mother) {
      drawPartnerLine(father, mother);
      drawChildLine(father, mother, child);
    } else {
      if (father) drawSingleParentLine(father, child);
      if (mother) drawSingleParentLine(mother, child);
    }
  }

  for (const person of pedigree.people) {
    drawPerson(person);
  }

  fillForm();
  fillPersonDatalist();
  renderErrors();
  deletePersonBtn.disabled = !selectedPerson();
}

function renderLegacy() {
  personPanel.hidden = true;
  legacyPanel.hidden = false;
  setToolbarForLegacy(true);
  errorsEl.innerHTML = "";
  const columns = Number(pedigree.columns || 0);
  const rows = Number(pedigree.rows || 0);
  const cellW = 27;
  const cellH = 22;
  const marginX = 12;
  const marginY = 12;
  const width = columns * cellW + marginX * 2;
  const height = rows * cellH + marginY * 2;
  canvas.setAttribute("viewBox", `0 0 ${width} ${height}`);
  canvas.style.minWidth = `${width}px`;
  canvas.style.minHeight = `${height}px`;

  const lineGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
  lineGroup.setAttribute("stroke", "#111111");
  lineGroup.setAttribute("stroke-width", "2");
  lineGroup.setAttribute("fill", "none");
  linksLayer.append(lineGroup);

  for (let index = 0; index < pedigree.cells.length; index += 1) {
    const { col, row } = legacyCellPosition(index);
    const x = marginX + col * cellW;
    const y = marginY + row * cellH;
    drawLegacyLine(lineGroup, pedigree.cells[index], x, y, cellW, cellH);
  }

  for (let index = 0; index < pedigree.cells.length; index += 1) {
    const { col, row } = legacyCellPosition(index);
    const x = marginX + col * cellW;
    const y = marginY + row * cellH;
    drawLegacySymbol(nodesLayer, pedigree.cells[index], x, y, cellW, cellH);
    drawLegacyNote(nodesLayer, pedigree.cells[index], x, y, cellW, cellH);
    const hit = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    hit.setAttribute("x", x);
    hit.setAttribute("y", y);
    hit.setAttribute("width", cellW);
    hit.setAttribute("height", cellH);
    hit.setAttribute("class", `legacy-cell ${selectedCell === index ? "selected" : ""}`);
    hit.dataset.index = String(index);
    hit.addEventListener("click", onLegacyCellClick);
    nodesLayer.append(hit);
  }
  updateLegacyPanel();
}

function drawPartnerLine(left, right) {
  const y = Math.min(left.y, right.y);
  appendPath(`M ${left.x} ${y} L ${right.x} ${y}`);
}

function drawChildLine(parentA, parentB, child) {
  const midX = (parentA.x + parentB.x) / 2;
  const parentY = Math.min(parentA.y, parentB.y);
  const junctionY = parentY + 55;
  appendPath(`M ${midX} ${parentY} L ${midX} ${junctionY} L ${child.x} ${junctionY} L ${child.x} ${child.y - 28}`);
}

function drawSingleParentLine(parent, child) {
  const midY = (parent.y + child.y) / 2;
  appendPath(`M ${parent.x} ${parent.y + 28} L ${parent.x} ${midY} L ${child.x} ${midY} L ${child.x} ${child.y - 28}`);
}

function appendPath(d) {
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  path.setAttribute("class", "relationship");
  linksLayer.append(path);
}

function drawPerson(person) {
  const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
  group.setAttribute("class", `person-node ${person.individual_id === selectedId ? "selected" : ""}`);
  group.setAttribute("transform", `translate(${person.x}, ${person.y})`);
  group.dataset.id = person.individual_id;

  const affected = person.phenotype && !["0", "-9", "unknown", "unaffected"].includes(person.phenotype.toLowerCase());
  let symbol;
  if (person.sex === "1") {
    symbol = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    symbol.setAttribute("x", "-24");
    symbol.setAttribute("y", "-24");
    symbol.setAttribute("width", "48");
    symbol.setAttribute("height", "48");
  } else if (person.sex === "2") {
    symbol = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    symbol.setAttribute("r", "24");
  } else {
    symbol = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    symbol.setAttribute("points", "0,-28 28,0 0,28 -28,0");
  }
  symbol.setAttribute("class", `symbol ${affected ? "affected" : ""}`);

  const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
  label.setAttribute("class", "node-label");
  label.setAttribute("y", "34");
  label.textContent = person.individual_id;

  group.append(symbol, label);
  group.addEventListener("pointerdown", startDrag);
  group.addEventListener("click", () => {
    selectedId = person.individual_id;
    render();
  });
  nodesLayer.append(group);
}

function startDrag(event) {
  event.preventDefault();
  const id = event.currentTarget.dataset.id;
  const person = findPerson(id);
  if (!person) return;
  selectedId = id;
  const point = svgPoint(event);
  drag = { id, dx: point.x - person.x, dy: point.y - person.y };
  draggedNode = event.currentTarget;
  window.addEventListener("pointermove", moveDrag);
  window.addEventListener("pointerup", endDrag, { once: true });
}

function moveDrag(event) {
  if (!drag) return;
  const person = findPerson(drag.id);
  const point = svgPoint(event);
  person.x = Math.round(point.x - drag.dx);
  person.y = Math.round(point.y - drag.dy);
  if (draggedNode) {
    draggedNode.setAttribute("transform", `translate(${person.x}, ${person.y})`);
  }
  linksLayer.replaceChildren();
  const people = new Map(pedigree.people.map((item) => [item.individual_id, item]));
  for (const child of pedigree.people) {
    const father = people.get(child.paternal_id);
    const mother = people.get(child.maternal_id);
    if (father && mother) {
      drawPartnerLine(father, mother);
      drawChildLine(father, mother, child);
    } else {
      if (father) drawSingleParentLine(father, child);
      if (mother) drawSingleParentLine(mother, child);
    }
  }
  fields.x.value = Math.round(person.x);
  fields.y.value = Math.round(person.y);
}

function endDrag(event) {
  window.removeEventListener("pointermove", moveDrag);
  drag = null;
  draggedNode = null;
  render();
  markDirty("Position geändert");
}

function svgPoint(event) {
  const point = canvas.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  return point.matrixTransform(canvas.getScreenCTM().inverse());
}

function fillForm() {
  const person = selectedPerson();
  for (const input of Object.values(fields)) input.disabled = !person;
  form.querySelector("button").disabled = !person;
  if (!person) {
    form.reset();
    return;
  }
  fields.individual_id.value = person.individual_id;
  fields.family_id.value = person.family_id;
  fields.sex.value = person.sex;
  fields.phenotype.value = person.phenotype;
  fields.paternal_id.value = person.paternal_id;
  fields.maternal_id.value = person.maternal_id;
  fields.x.value = Math.round(person.x ?? 0);
  fields.y.value = Math.round(person.y ?? 0);
}

function fillPersonDatalist() {
  personIdsEl.replaceChildren();
  const unknown = document.createElement("option");
  unknown.value = "0";
  personIdsEl.append(unknown);
  for (const person of pedigree.people) {
    const option = document.createElement("option");
    option.value = person.individual_id;
    personIdsEl.append(option);
  }
}

function renderErrors() {
  const errors = validateClient();
  errorsEl.innerHTML = "";
  for (const error of errors) {
    const line = document.createElement("div");
    line.textContent = error;
    errorsEl.append(line);
  }
}

function validateClient() {
  const ids = new Set(pedigree.people.map((person) => person.individual_id));
  const errors = [];
  for (const person of pedigree.people) {
    if (person.paternal_id !== "0" && !ids.has(person.paternal_id)) {
      errors.push(`${person.individual_id}: Vater-ID fehlt (${person.paternal_id})`);
    }
    if (person.maternal_id !== "0" && !ids.has(person.maternal_id)) {
      errors.push(`${person.individual_id}: Mutter-ID fehlt (${person.maternal_id})`);
    }
  }
  return errors;
}

function selectedPerson() {
  return findPerson(selectedId);
}

function findPerson(id) {
  return pedigree.people.find((person) => person.individual_id === id);
}

function nextId(prefix) {
  let index = 1;
  while (findPerson(`${prefix}${String(index).padStart(3, "0")}`)) {
    index += 1;
  }
  return `${prefix}${String(index).padStart(3, "0")}`;
}

function setStatus(message) {
  statusEl.textContent = message;
}

function markDirty() {
  dirty = true;
  setAutosaveState("dirty", "Ungesicherte Änderung");
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => savePedigree(), 1200);
}

function setAutosaveState(state, message) {
  autosaveStateEl.className = `autosave-state ${state}`;
  autosaveStateEl.textContent = message;
}

function exportSvg() {
  const exported = canvas.cloneNode(true);
  exported.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const viewBox = canvas.getAttribute("viewBox") || "0 0 1200 760";
  const [, , width = "1200", height = "760"] = viewBox.split(" ");
  exported.setAttribute("width", width);
  exported.setAttribute("height", height);

  const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
  style.textContent = `
    .relationship { fill: none; stroke: #566173; stroke-width: 2; }
    .symbol { fill: #fff; stroke: #1b2431; stroke-width: 2; }
    .symbol.affected { fill: #d8ebe7; }
    .person-node.selected .symbol { stroke: #1b2431; stroke-width: 2; }
    .node-label {
      font-family: Inter, Arial, sans-serif;
      font-size: 13px;
      text-anchor: middle;
      dominant-baseline: hanging;
      fill: #1c2430;
    }
  `;

  const metadata = document.createElementNS("http://www.w3.org/2000/svg", "metadata");
  metadata.setAttribute("data-format", isLegacyMode() ? "legacy-ped-grid" : "pedigree-lab-json");
  metadata.textContent = isLegacyMode() ? toLegacyPedText() : JSON.stringify({
    ped: toPedText(),
    pedigree,
  }, null, 2);
  exported.prepend(metadata, style);

  const serializer = new XMLSerializer();
  const blob = new Blob([serializer.serializeToString(exported)], {
    type: "image/svg+xml;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${selectedPerson()?.family_id || "pedigree"}.svg`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setStatus("SVG mit .ped-Metadaten exportiert");
}

function isLegacyMode() {
  return pedigree.mode === "legacy_grid";
}

function setToolbarForLegacy(isLegacy) {
  document.getElementById("addParentsBtn").disabled = isLegacy;
  document.getElementById("addChildBtn").disabled = isLegacy;
  document.getElementById("layoutBtn").disabled = isLegacy;
  deletePersonBtn.textContent = isLegacy ? "Zelle leeren" : "Entfernen";
}

function legacyCellPosition(index) {
  return {
    col: Math.floor(index / Number(pedigree.rows)),
    row: index % Number(pedigree.rows),
  };
}

function onLegacyCellClick(event) {
  const index = Number(event.currentTarget.dataset.index);
  selectedCell = index;
  const tool = legacyTool.value;
  if (tool !== "inspect") {
    pedigree.cells[index] = legacyCellForTool(tool, pedigree.cells[index]);
    markDirty();
  }
  render();
}

function updateLegacyPanel() {
  if (selectedCell == null) {
    legacyCellInfo.textContent = "Keine Zelle ausgewählt";
    legacyNote.value = "";
    return;
  }
  const { col, row } = legacyCellPosition(selectedCell);
  legacyCellInfo.textContent = `Zelle ${selectedCell + 1}, Spalte ${col + 1}, Reihe ${row + 1}`;
  legacyNote.value = extractLegacyNote(pedigree.cells[selectedCell]).join("\n");
}

function applyLegacyNote() {
  if (selectedCell == null) return;
  const existing = pedigree.cells[selectedCell] || "E";
  const note = legacyNote.value.trim();
  pedigree.cells[selectedCell] = setLegacyNote(existing, note);
  render();
  markDirty();
}

function deleteSelectedCell() {
  if (selectedCell == null) return;
  pedigree.cells[selectedCell] = "E";
  render();
  markDirty();
}

function legacyCellForTool(tool, existing) {
  const note = extractLegacyNote(existing).join("\\\\");
  const notePart = note ? `rk: 0~rmc: ~rw: ${note}\\\\~` : "";
  const cells = {
    empty: "E",
    male: `Mrf: {-1\\16777235\\}~${notePart}rn: mannc~`,
    female: `Wrf: {-1\\16777235\\}~${notePart}rn: frauc~`,
    diamond: `Srf: {-1\\16777235\\}~${notePart}rn: rautec~`,
    abort: "Srf: {-1\\16777216\\}~rn: abortc~",
    horizontal: "Lrn: horizontal~",
    vertical: "Lrn: vertikal~",
    junction: "Lrn: plus~",
    t_down: "Lrn: t~",
    t_up: "Lrn: treverse~",
    corner_up_right: "Lrn: l~",
    corner_up_left: "Lrn: lreverse~",
    corner_down_right: "Lrn: ldown~",
    corner_down_left: "Lrn: ldownreverse~",
  };
  return cells[tool] || existing || "E";
}

function setLegacyNote(cell, note) {
  const symbol = legacySymbolType(cell);
  if (!symbol) return cell;
  const tool = symbol === "Mrf" ? "male" : symbol === "Wrf" ? "female" : cell.includes("abortc") ? "abort" : "diamond";
  const clean = note.replaceAll("\n", "\\\\");
  const notePart = clean ? `rk: 0~rmc: ~rw: ${clean}\\\\~` : "";
  const cells = {
    male: `Mrf: {-1\\16777235\\}~${notePart}rn: mannc~`,
    female: `Wrf: {-1\\16777235\\}~${notePart}rn: frauc~`,
    diamond: `Srf: {-1\\16777235\\}~${notePart}rn: rautec~`,
    abort: `Srf: {-1\\16777216\\}~${notePart}rn: abortc~`,
  };
  return cells[tool];
}

function legacySymbolType(cell) {
  if (cell.startsWith("Mrf:")) return "Mrf";
  if (cell.startsWith("Wrf:")) return "Wrf";
  if (cell.startsWith("Srf:")) return "Srf";
  return null;
}

function extractLegacyNote(cell) {
  const match = String(cell || "").match(/rw:\s*(.*?)~rn:/);
  if (!match) return [];
  return match[1].split(/\\\\|\\/).map((part) => part.trim()).filter(Boolean);
}

function drawLegacyLine(parent, cell, x, y, cellW, cellH) {
  for (const [x1, y1, x2, y2] of legacyLineSegments(cell, x, y, cellW, cellH)) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", x1);
    line.setAttribute("y1", y1);
    line.setAttribute("x2", x2);
    line.setAttribute("y2", y2);
    parent.append(line);
  }
}

function drawLegacySymbol(parent, cell, x, y, cellW, cellH) {
  const type = legacySymbolType(cell);
  if (!type) return;
  const cx = x + cellW / 2;
  const cy = y + cellH / 2;
  const size = Math.min(cellW, cellH) * 0.72;
  const half = size / 2;
  const fill = cell.includes("abortc") || cell.includes("\\16777216\\") ? "#111111" : "#ffffff";
  let symbol;
  if (type === "Mrf") {
    symbol = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    symbol.setAttribute("x", cx - half);
    symbol.setAttribute("y", cy - half);
    symbol.setAttribute("width", size);
    symbol.setAttribute("height", size);
  } else if (type === "Wrf") {
    symbol = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    symbol.setAttribute("cx", cx);
    symbol.setAttribute("cy", cy);
    symbol.setAttribute("r", half);
  } else {
    symbol = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    symbol.setAttribute("points", `${cx},${cy - half} ${cx + half},${cy} ${cx},${cy + half} ${cx - half},${cy}`);
  }
  symbol.setAttribute("fill", fill);
  symbol.setAttribute("stroke", "#111111");
  symbol.setAttribute("stroke-width", "2");
  parent.append(symbol);
}

function drawLegacyNote(parent, cell, x, y, cellW, cellH) {
  const notes = extractLegacyNote(cell);
  const cx = x + cellW / 2;
  const cy = y + cellH / 2;
  notes.forEach((note, offset) => {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", cx + 12);
    text.setAttribute("y", cy - 4 + offset * 12);
    text.setAttribute("class", "legacy-note");
    text.textContent = note;
    parent.append(text);
  });
  if (cell.includes("rmc: pfeil")) {
    appendLegacyPath(parent, `M ${cx - 18} ${cy + 17} L ${cx - 6} ${cy + 6}`);
    appendLegacyPath(parent, `M ${cx - 12} ${cy + 8} L ${cx - 6} ${cy + 6} L ${cx - 8} ${cy + 12}`);
  }
}

function appendLegacyPath(parent, d) {
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  path.setAttribute("stroke", "#111111");
  path.setAttribute("fill", "none");
  path.setAttribute("stroke-width", "2");
  parent.append(path);
}

function legacyLineSegments(cell, x, y, cellW, cellH) {
  if (!String(cell).startsWith("Lrn:")) return [];
  const kind = cell.split(":", 2)[1].split("~", 1)[0].trim();
  const cx = x + cellW / 2;
  const cy = y + cellH / 2;
  const left = x;
  const right = x + cellW;
  const top = y;
  const bottom = y + cellH;
  const segments = {
    horizontal: [[left, cy, right, cy]],
    vertikal: [[cx, top, cx, bottom]],
    plus: [[left, cy, right, cy], [cx, top, cx, bottom]],
    t: [[left, cy, right, cy], [cx, cy, cx, bottom]],
    treverse: [[left, cy, right, cy], [cx, top, cx, cy]],
    tstop: [[cx, top, cx, cy]],
    l: [[cx, cy, right, cy], [cx, top, cx, cy]],
    ldown: [[cx, cy, right, cy], [cx, cy, cx, bottom]],
    lreverse: [[left, cy, cx, cy], [cx, top, cx, cy]],
    ldownreverse: [[left, cy, cx, cy], [cx, cy, cx, bottom]],
  };
  return segments[kind] || [];
}

function toLegacyPedText() {
  return [
    pedigree.title || "PED PedigreeLab",
    pedigree.settings || `colRows: ${pedigree.columns} @ ${pedigree.rows}~`,
    ...(pedigree.cells || []),
    "~~~",
  ].join("\n");
}

function toPedText() {
  const lines = [];
  for (const comment of pedigree.comments || []) {
    if (!comment.startsWith("# PedigreeLab position ")) {
      lines.push(comment.startsWith("#") ? comment : `# ${comment}`);
    }
  }
  for (const person of pedigree.people) {
    if (person.x != null && person.y != null) {
      lines.push(`# PedigreeLab position ${person.individual_id} ${Number(person.x).toFixed(1)} ${Number(person.y).toFixed(1)}`);
    }
  }
  for (const person of pedigree.people) {
    lines.push([
      person.family_id || "FAM1",
      person.individual_id,
      person.paternal_id || "0",
      person.maternal_id || "0",
      person.sex || "0",
      person.phenotype || "0",
      ...(person.extra_columns || []),
    ].join(" "));
  }
  return `${lines.join("\n")}\n`;
}
