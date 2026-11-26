const state = {
  connected: false,
  pid: null,
  project: null,
  schematic: null,
  elements: [],
  wires: [],
  graph: null,
  activity: [],
  lastSeq: 0,
  waiting: false,
  permQueue: [],
  permCurrent: null,
  theme: localStorage.getItem("fieldnote-theme") || "dark",
};

const $ = (id) => document.getElementById(id);

// Tools that never change AWR; their activity does not trigger a project refresh.
const READ_ONLY = new Set([
  "project_info", "list_elements", "list_wires", "get_parameters", "graph_data", "graph_image", "status_messages",
  "simulation_state", "em_info", "em_ports", "search_models", "check_em_setup", "em_simulation_log", "reply",
]);
const DESTRUCTIVE = /(save_project|new_project|delete_)/;

// Every backend call goes through pywebview; the backend returns {result} or {error}.
async function api(method, ...args) {
  const fn = window.pywebview?.api?.[method];
  if (!fn) throw new Error("Fieldnote backend is not ready.");
  const reply = await fn(...args);
  if (reply && reply.error) throw new Error(typeof reply.error === "string" ? reply.error : JSON.stringify(reply.error));
  return reply ? reply.result : undefined;
}

const callTool = (tool, args = {}) => api("call", tool, args);

function toast(message, error = false) {
  const node = document.createElement("div");
  node.className = `toast${error ? " error" : ""}`;
  node.textContent = message;
  $("toastRegion").append(node);
  window.setTimeout(() => node.remove(), 4400);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function placeholder(text) {
  return el("div", "list-placeholder", text);
}

function short(value, max = 90) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  const flat = (text ?? "").replace(/\s+/g, " ");
  return flat.length > max ? `${flat.slice(0, max)}…` : flat;
}

/* ---------- Session / connection ---------- */

function setSession(connected, label, detail) {
  state.connected = connected;
  const dot = document.querySelector(".pulse-dot");
  dot.classList.toggle("connected", connected);
  dot.classList.toggle("disconnected", !connected);
  $("connectionLabel").textContent = label;
  $("connectionDetail").textContent = detail;
  $("chatSubtitle").textContent = connected ? "Messages go to your linked Claude Code session" : "Connect a Claude Code session to start";
  if (!connected) {
    setWaiting(false);
    $("saveState").textContent = "Not connected";
  }
}

async function findSessions() {
  if (findSessions.busy) return; // pywebviewready and DOMContentLoaded can both fire at start-up
  findSessions.busy = true;
  try {
    const sessions = (await api("sessions")) || [];
    const picker = $("sessionPicker");
    picker.replaceChildren(new Option(sessions.length ? "Choose a session" : "No session found", ""));
    for (const session of sessions) picker.add(new Option(`Session ${session.pid}`, String(session.pid)));
    if (state.pid && sessions.some((s) => s.pid === state.pid)) picker.value = String(state.pid);
    if (!state.connected && sessions.length === 1) {
      picker.value = String(sessions[0].pid);
      await connectSession(sessions[0].pid);
    }
  } catch (error) {
    toast(error.message, true);
  } finally {
    findSessions.busy = false;
  }
}

async function connectSession(pid) {
  if (!pid) return;
  try {
    await api("connect", Number(pid));
    onHello(Number(pid));
  } catch (error) {
    setSession(false, "Not connected", error.message);
    toast(error.message, true);
  }
}

function onHello(pid) {
  if (pid) state.pid = pid;
  setSession(true, `Linked to session ${state.pid ?? ""}`.trim(), "Waiting for the AWR project…");
  if (state.pid) $("sessionPicker").value = String(state.pid);
  loadBacklog();
  refreshProject();
}

function onDisconnected() {
  setSession(false, "Disconnected", "The Claude Code session ended. Pick a session or start a new one.");
  state.project = null;
  renderProject();
  findSessions();
}

async function startLinked() {
  try {
    const result = await api("start_linked_session");
    $("startCommand").textContent = result.command || "(no command returned)";
    toast("Linked session started. Command is shown under Settings.");
    window.setTimeout(findSessions, 3000);
  } catch (error) {
    toast(error.message, true);
  }
}

/* ---------- Project panel ---------- */

let refreshTimer = null;
function scheduleRefresh() {
  window.clearTimeout(refreshTimer);
  refreshTimer = window.setTimeout(refreshProject, 1000);
}

async function refreshProject() {
  if (!state.connected) return;
  try {
    const info = await callTool("project_info");
    state.project = info;
    $("saveState").textContent = info.saved ? "Saved in AWR" : "Unsaved changes in AWR";
    $("saveState").previousElementSibling.classList.toggle("connected", !!info.saved);
    const label = info.project || "AWR project";
    setSession(true, label, `Session ${state.pid ?? "?"} · ${info.file || "not saved yet"}`);
    if (state.schematic && !info.schematics.includes(state.schematic)) state.schematic = null;
    if (state.graph && !info.graphs.includes(state.graph)) state.graph = null;
    renderProject();
    if (state.schematic) await refreshSchematic();
    else renderParts();
  } catch (error) {
    setSession(true, `Linked to session ${state.pid ?? ""}`.trim(), `AWR: ${error.message}`);
    state.project = null;
    renderProject();
  }
}

function renderProject() {
  const info = state.project;
  $("projectName").textContent = info ? info.project : "No AWR project";
  $("projectFile").textContent = info ? info.file || "Unsaved AWR project" : "Microwave Office · v17";
  $("schematicCount").textContent = info ? String(info.schematics.length) : "—";
  $("graphCount").textContent = info ? String(info.graphs.length) : "0";
  renderSchematicList();
  renderExtras();
  renderGraphList();
}

function renderSchematicList() {
  const list = $("schematicList");
  list.replaceChildren();
  if (!state.project || !state.project.schematics.length) {
    list.append(placeholder(state.project ? "No schematics yet. Ask Claude to create one." : "Waiting for AWR project…"));
    return;
  }
  for (const name of state.project.schematics) {
    const button = el("button", `schematic-row${name === state.schematic ? " active" : ""}`);
    button.type = "button";
    button.append(el("span", "schematic-row-icon", "⌁"), el("span", "schematic-row-name", name), el("span", "schematic-row-open", name === state.schematic ? "●" : "↗"));
    button.addEventListener("click", () => selectSchematic(name));
    list.append(button);
  }
}

function renderExtras() {
  const box = $("projectExtras");
  box.replaceChildren();
  const info = state.project;
  if (!info) return;
  for (const [title, items] of [["GRAPHS", info.graphs], ["EM STRUCTURES", info.em_structures], ["NETLISTS", info.netlists]]) {
    if (!items || !items.length) continue;
    box.append(el("b", "", title));
    for (const item of items) box.append(el("div", "", item));
  }
}

async function selectSchematic(name) {
  state.schematic = name;
  renderSchematicList();
  await refreshSchematic();
}

async function refreshSchematic() {
  if (!state.schematic) return renderParts();
  try {
    const [elements, wires] = await Promise.all([
      callTool("list_elements", { schematic: state.schematic }),
      callTool("list_wires", { schematic: state.schematic }),
    ]);
    state.elements = elements || [];
    state.wires = wires || [];
    renderParts();
  } catch (error) {
    toast(error.message, true);
  }
}

function renderParts() {
  const body = $("partsBody");
  body.replaceChildren();
  $("partCount").textContent = state.schematic ? String(state.elements.length) : "—";
  $("wireCount").textContent = state.schematic ? String(state.wires.length) : "—";
  $("breadcrumbName").textContent = document.querySelector(".nav-link.active")?.querySelector("span:nth-child(2)")?.textContent || "Design";
  if (!state.schematic) {
    $("partsTitle").textContent = "Select a schematic";
    body.append(placeholder("Choose a schematic under Project files to see its parts and wires."));
    return;
  }
  $("partsTitle").textContent = state.schematic;
  if (!state.elements.length) {
    body.append(placeholder("This schematic is empty. Ask Claude to add parts."));
    return;
  }
  const table = el("table", "parts-table");
  const head = el("tr");
  for (const title of ["ELEMENT", "MODEL", "KEY PARAMETERS", "PINS"]) head.append(el("th", "", title));
  table.append(head);
  for (const element of state.elements) {
    const params = (element.parameters || []).filter((p) => p.name !== "ID")
      .map((p) => `${p.name}=${p.value}${p.unit ? ` ${p.unit}` : ""}`).join(", ");
    const pins = (element.pins || []).map((p) => `${p.pin}${p.connected ? `→net ${p.net}` : " open"}`).join("  ");
    const row = el("tr");
    row.append(el("td", "", element.id), el("td", "", element.model), el("td", "", params || "—"), el("td", "", pins || "—"));
    table.append(row);
  }
  body.append(table);
  body.append(el("div", "parts-sub", `WIRES (${state.wires.length})`));
  if (!state.wires.length) {
    body.append(placeholder("No wires."));
    return;
  }
  const wires = el("table", "parts-table");
  const wireHead = el("tr");
  for (const title of ["FROM", "TO"]) wireHead.append(el("th", "", title));
  wires.append(wireHead);
  for (const wire of state.wires) {
    const row = el("tr");
    row.append(el("td", "", `(${wire.x1}, ${wire.y1})`), el("td", "", `(${wire.x2}, ${wire.y2})`));
    wires.append(row);
  }
  body.append(wires);
}

/* ---------- Chat ---------- */

function setWaiting(on) {
  state.waiting = on;
  $("chatWait").classList.toggle("hidden", !on);
}

function addBubble(kind, text) {
  $("chatEmpty")?.remove();
  const log = $("chatLog");
  log.append(el("div", `chat-msg ${kind}`, text));
  log.scrollTop = log.scrollHeight;
}

async function sendChat(event) {
  event.preventDefault();
  const text = $("chatInput").value.trim();
  if (!text) return;
  if (!state.connected) return toast("Connect a Claude Code session first.", true);
  try {
    await api("chat", text);
    addBubble("user", text);
    $("chatInput").value = "";
    setWaiting(true);
  } catch (error) {
    toast(error.message, true);
  }
}

function askClaude(text) {
  $("chatInput").value = text;
  switchView("design");
  $("chatInput").focus();
}

const current = () => state.schematic || "<schematic name>";
const ASKS = {
  "new-schematic": () => "Create a schematic named ",
  "add-part": () => `Add a part to schematic ${current()} and wire it tidily: `,
  simulate: () => `Run the simulation for schematic ${current()} and show me the results.`,
};

/* ---------- Activity ---------- */

async function loadBacklog() {
  try {
    const entries = (await api("activity", state.lastSeq)) || [];
    for (const entry of entries) addActivity(entry, false);
  } catch (error) {
    toast(error.message, true);
  }
}

function addActivity(entry, live = true) {
  if (entry.seq !== undefined) {
    if (state.activity.some((e) => e.seq === entry.seq)) return;
    state.lastSeq = Math.max(state.lastSeq, entry.seq);
  }
  state.activity.push(entry);
  $("activityEmpty")?.remove();
  $("activityCount").textContent = String(state.activity.length);
  const failed = entry.ok === false;
  const row = el("div", `activity-row${failed ? " bad" : ""}`);
  const top = el("div", "activity-top");
  const dot = el("i", "pin-status connected");
  top.append(dot, el("span", "activity-tool", entry.tool || "?"), el("span", "activity-meta", `${entry.source || "claude"} · ${failed ? "error" : "ok"} · ${entry.ms ?? "?"} ms`));
  row.append(top, el("div", "activity-args", short(entry.args || {})));
  let detail = null;
  row.addEventListener("click", () => {
    if (detail) {
      detail.remove();
      detail = null;
      return;
    }
    detail = el("pre", "activity-result", short(entry.result_or_error ?? "", 4000));
    row.append(detail);
  });
  const list = $("activityList");
  list.prepend(row);
  while (list.children.length > 80) list.lastChild.remove();
  if (live && !READ_ONLY.has(entry.tool)) scheduleRefresh();
}

/* ---------- Results viewer ---------- */

function renderGraphList() {
  const list = $("graphList");
  list.replaceChildren();
  const graphs = state.project?.graphs || [];
  if (!graphs.length) {
    list.append(placeholder(state.project ? "No graphs yet. Ask Claude to simulate." : "Waiting for AWR project…"));
    return;
  }
  for (const name of graphs) {
    const button = el("button", `schematic-row${name === state.graph ? " active" : ""}`);
    button.type = "button";
    button.append(el("span", "schematic-row-icon", "◉"), el("span", "schematic-row-name", name), el("span", "schematic-row-open", name === state.graph ? "●" : "↗"));
    button.addEventListener("click", () => selectGraph(name));
    list.append(button);
  }
}

async function selectGraph(name) {
  state.graph = name;
  renderGraphList();
  setSimulationStatus("Loading graph…", "busy");
  $("resultsSubtitle").textContent = name;
  try {
    const [image, summaries] = await Promise.all([
      callTool("graph_image", { graph: name }),
      callTool("graph_data", { graph: name, summary: true }),
    ]);
    renderResults(name, image, summaries || []);
    setSimulationStatus("Loaded.", "success");
  } catch (error) {
    setSimulationStatus(error.message, "error");
    $("resultsPlaceholder").classList.add("hidden");
    const content = $("resultsContent");
    content.classList.remove("hidden");
    content.replaceChildren(el("div", "result-error", error.message));
  }
}

function setSimulationStatus(text, type = "") {
  const status = $("simulationStatus");
  status.textContent = text;
  status.className = `simulation-status${type ? ` ${type}` : ""}`;
}

function renderResults(graph, image, summaries) {
  $("resultsPlaceholder").classList.add("hidden");
  const content = $("resultsContent");
  content.classList.remove("hidden");
  content.replaceChildren();
  const meta = el("div", "result-meta");
  meta.append(el("span", "", graph), el("span", "", `${summaries.length} trace${summaries.length === 1 ? "" : "s"}`));
  content.append(meta);
  if (image && image.image_base64) {
    const img = el("img", "result-image");
    img.alt = `Plot of ${graph}`;
    img.src = `data:${image.mime || "image/png"};base64,${image.image_base64}`;
    content.append(img);
  }
  const cards = el("div", "result-summary");
  for (const summary of summaries) {
    if (summary.min === undefined) continue;
    const card = el("div", "metric-card");
    const unit = summary.y_unit || "";
    card.append(
      el("span", "", summary.label || summary.measurement || "trace"),
      el("strong", "", `Min ${Number(summary.min).toPrecision(4)} ${unit}`),
      el("span", "", `at ${formatFrequency(summary.x_at_min)} ${summary.x_unit || ""}`),
      el("strong", "", `Max ${Number(summary.max).toPrecision(4)} ${unit}`),
      el("span", "", `at ${formatFrequency(summary.x_at_max)} ${summary.x_unit || ""}`),
    );
    cards.append(card);
  }
  content.append(cards);
  $("resultsSubtitle").textContent = `${summaries.length} trace${summaries.length === 1 ? "" : "s"} · ${graph}`;
}

function formatFrequency(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "—");
  if (Math.abs(number) >= 1e9) return `${(number / 1e9).toFixed(2)}G`;
  if (Math.abs(number) >= 1e6) return `${(number / 1e6).toFixed(2)}M`;
  if (Math.abs(number) >= 1e3) return `${(number / 1e3).toFixed(2)}k`;
  return number.toPrecision(3);
}

/* ---------- Library ---------- */

async function searchLibrary() {
  const query = $("modelSearch").value.trim();
  if (!query) {
    $("modelSearch").focus();
    return;
  }
  if (!state.connected) return toast("Connect a Claude Code session first.", true);
  const results = $("modelResults");
  results.replaceChildren(el("div", "model-loading", "Searching the AWR model library…"));
  $("modelResultCount").textContent = "Searching…";
  try {
    const found = await callTool("search_models", { query, limit: 20 });
    const models = found?.models || [];
    results.replaceChildren();
    if (!models.length) results.append(placeholder("No AWR models matched that search."));
    $("modelResultCount").textContent = `${models.length} matching model${models.length === 1 ? "" : "s"}`;
    for (const model of models) results.append(createModelRow(model));
  } catch (error) {
    results.replaceChildren();
    $("modelResultCount").textContent = "Search unavailable";
    toast(error.message, true);
  }
}

function createModelRow(model) {
  const row = el("div", "model-row");
  const name = el("span", "model-name", model.name);
  name.title = model.name;
  const desc = el("span", "model-desc", model.description || "AWR model");
  desc.title = desc.textContent;
  const category = el("span", "model-category", model.category || `${model.pins} pins`);
  category.title = category.textContent;
  const add = el("button", "button button-small button-soft model-add", "Use this part");
  add.type = "button";
  add.addEventListener("click", () => askClaude(`Add ${model.name} to schematic ${current()} and wire it tidily`));
  row.append(name, desc, category, add);
  return row;
}

/* ---------- Approvals ---------- */

function onPermissionRequest(evt) {
  state.permQueue.push(evt);
  showPermission();
}

function showPermission() {
  if (state.permCurrent || !state.permQueue.length) return;
  const evt = state.permQueue.shift();
  state.permCurrent = evt;
  const destructive = DESTRUCTIVE.test(evt.tool_name || "");
  $("permModal").classList.toggle("destructive", destructive);
  $("permKicker").textContent = destructive ? "DESTRUCTIVE ACTION — CHECK CAREFULLY" : "APPROVAL NEEDED";
  $("permTool").textContent = evt.tool_name || "Tool request";
  $("permDesc").textContent = evt.description || "";
  $("permInput").textContent = evt.input_preview || "";
  $("permQueue").textContent = state.permQueue.length ? `${state.permQueue.length} more waiting` : "";
  if (!$("permModal").open) $("permModal").showModal();
}

async function answerPermission(decision) {
  const evt = state.permCurrent;
  if (!evt) return;
  state.permCurrent = null;
  $("permModal").close();
  try {
    await api("permission", evt.request_id, decision);
  } catch (error) {
    toast(error.message, true);
  }
  showPermission();
}

/* ---------- Settings ---------- */

async function loadSettings() {
  try {
    const s = await api("settings");
    $("settingsWorkspace").value = s.workspace || "";
    $("settingsClaude").value = s.claude_path || "";
    $("claudeFound").textContent = s.claude_found ? "Claude Code found" : "Claude Code not found";
    $("settingsMode").value = "linked";
  } catch (error) {
    $("claudeFound").textContent = "Unavailable";
    toast(error.message, true);
  }
}

async function saveSettings() {
  try {
    await api("save_settings", { workspace: $("settingsWorkspace").value.trim(), claude_path: $("settingsClaude").value.trim(), mode: "linked" });
    toast("Settings saved.");
    await loadSettings();
  } catch (error) {
    toast(error.message, true);
  }
}

/* ---------- Shell ---------- */

function switchView(name) {
  const views = { design: "designView", simulation: "simulationView", library: "libraryView", settings: "settingsView" };
  for (const [key, id] of Object.entries(views)) $(id).classList.toggle("active", key === name);
  document.querySelectorAll(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  $("breadcrumbName").textContent = name === "design" && state.schematic ? state.schematic : name[0].toUpperCase() + name.slice(1);
  if (name === "settings") loadSettings();
}

function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  document.body.classList.toggle("theme-light", state.theme === "light");
  localStorage.setItem("fieldnote-theme", state.theme);
}

// Python calls this to push events.
window.fieldnoteEvent = (evt) => {
  if (!evt || !evt.event) return;
  switch (evt.event) {
    case "hello": onHello(evt.pid); break;
    case "activity": addActivity(evt); break;
    case "reply":
      addBubble("claude", evt.text || "");
      setWaiting(false);
      break;
    case "permission_request": onPermissionRequest(evt); break;
    case "disconnected": onDisconnected(); break;
    default: break;
  }
};

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
  document.querySelectorAll("[data-ask]").forEach((button) => button.addEventListener("click", () => askClaude(ASKS[button.dataset.ask]())));
  $("newSchematicLink").addEventListener("click", () => askClaude(ASKS["new-schematic"]()));
  $("askSimulate").addEventListener("click", () => askClaude(ASKS.simulate()));
  $("refreshConnection").addEventListener("click", async () => {
    await findSessions();
    refreshProject();
  });
  $("sessionPicker").addEventListener("change", (event) => connectSession(event.target.value));
  $("startLinked").addEventListener("click", startLinked);
  $("startLinkedSettings").addEventListener("click", startLinked);
  $("refreshSchematic").addEventListener("click", refreshProject);
  $("refreshResults").addEventListener("click", async () => {
    await refreshProject();
    if (state.graph) selectGraph(state.graph);
  });
  $("chatForm").addEventListener("submit", sendChat);
  $("chatInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) $("chatForm").requestSubmit();
    if (event.key === "Enter" && !event.shiftKey) event.preventDefault();
  });
  $("searchModels").addEventListener("click", searchLibrary);
  $("modelSearch").addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchLibrary();
  });
  document.querySelectorAll(".library-hints button").forEach((button) => button.addEventListener("click", () => {
    $("modelSearch").value = button.dataset.query;
    searchLibrary();
  }));
  $("saveSettings").addEventListener("click", saveSettings);
  $("permAllow").addEventListener("click", () => answerPermission("allow"));
  $("permDeny").addEventListener("click", () => answerPermission("deny"));
  // An approval must be answered explicitly; Escape must not dismiss it.
  $("permModal").addEventListener("cancel", (event) => event.preventDefault());
  $("themeToggle").addEventListener("click", toggleTheme);
}

if (state.theme === "light") document.addEventListener("DOMContentLoaded", () => document.body.classList.add("theme-light"));
document.addEventListener("DOMContentLoaded", bindEvents);
window.addEventListener("pywebviewready", findSessions);
document.addEventListener("DOMContentLoaded", () => { if (window.pywebview?.api) findSessions(); });
