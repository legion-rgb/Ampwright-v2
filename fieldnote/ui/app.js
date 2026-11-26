// Fieldnote window. The backend owns the state; this page renders it. No browser storage: the html= page has none.
const $ = (id) => document.getElementById(id);

const PORT_TEXT = {
  claude: { off: "Waiting", connecting: "Starting", up: "Running", error: "Stopped" },
  awr: { off: "Waiting", connecting: "Reading project", up: "Connected", error: "Not reachable" },
};

function api(method, ...args) {
  const fn = window.pywebview?.api?.[method];
  return fn ? fn(...args) : Promise.reject(new Error("The Fieldnote backend isn't ready."));
}

function showBanner(text) {
  $("bannerText").textContent = text;
  $("banner").hidden = !text;
}
// Any failure in this page is shown, never a silent blank window.
window.addEventListener("error", (e) => showBanner(`The window hit an error: ${e.message}`));
window.addEventListener("unhandledrejection", (e) => showBanner(`The window hit an error: ${e.reason?.message || e.reason}`));

function onState(s) {
  for (const key of ["claude", "awr"]) {
    document.querySelector(`.seg[data-seg="${key}"]`).dataset.state = s[key];
    document.querySelector(`.port[data-port="${key}"]`).dataset.state = s[key];
  }
  $("claudeState").textContent = PORT_TEXT.claude[s.claude];
  $("awrState").textContent = s.awr === "up" && s.project ? projectTitle(s.project) : PORT_TEXT.awr[s.awr];
  const failed = s.claude === "error" || s.awr === "error";
  showBanner(failed ? s.detail : "");
  $("detail").textContent = failed ? "" : s.detail;
  renderProject(s.project, failed ? s.detail : "");
  const working = s.turn === "working";
  $("working").hidden = !working;
  $("stop").hidden = !working;
  $("send").hidden = working;
  $("task").disabled = $("send").disabled = s.claude !== "up" || working;
  renderMode(s.mode || "quick", working || s.claude === "connecting");
}

// ---- Quick / Design mode: a switch restarts Claude Code, so it is locked during a turn ----
const MODE_TEXT = {
  quick: ["Describe a circuit", "Claude Code builds it in AWR. Each step shows up here as it happens, and the AWR window shows the result.",
          "Describe a circuit, for example a 2 GHz low-pass filter on FR4"],
  design: ["Describe a design goal", "Claude writes a spec and waits for you to approve it. Then the design team works out the theory, builds it in AWR, checks it against the spec and fixes what fails.",
           "Describe a design goal, for example a 5th-order 2 GHz Chebyshev low-pass on FR4"],
};

function renderMode(mode, locked) {
  for (const b of document.querySelectorAll(".mode button")) {
    b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
    b.disabled = locked;
  }
  const [title, text, hint] = MODE_TEXT[mode] || MODE_TEXT.quick;
  $("emptyTitle").textContent = title;
  $("emptyText").textContent = text;
  $("task").placeholder = hint;
}

async function setMode(mode) {
  const r = await api("set_mode", mode);
  if (!r.ok) showBanner(r.error);
}

// ---- chat and progress feed: every change arrives as the full history ----
const STEP_ICON = [[/graph|measurement/, "i-graph"], [/simulat|frequenc|optim|sweep|status/, "i-sim"], [/^(em_|.*_em_|.*em_structure)/, "i-em"],
                   [/schematic|element|shunt|port|ground|connect|parameter|equation/, "i-schematic"]];
const STATUS_TEXT = { running: "Running", done: "Done", failed: "Failed", stopped: "Stopped", denied: "Denied" };
const el = (tag, cls, text) => Object.assign(document.createElement(tag), { className: cls || "", textContent: text ?? "" });

function stepRow(it) {
  // shortcut: nesting is by indent only, in arrival order; parallel subagents would interleave. Group by parent if that happens.
  const row = el("div", "step" + (it.agent ? " agent" : "") + (it.parent ? " sub" : ""));
  row.dataset.status = it.status;
  const icon = it.agent ? "i-source" : (STEP_ICON.find(([re]) => re.test(it.tool)) || [0, "i-netlist"])[1];
  row.innerHTML = `<svg><use href="#${icon}"/></svg>`;
  row.append(el("span", "tool", it.tool.replaceAll("_", " ")), el("span", "sum", it.summary), el("span", "st", STATUS_TEXT[it.status] || it.status),
             el("span", "tm", it.t));
  if (it.error) row.append(el("span", "err", it.error));
  return row;
}

// ---- approval dialog: shown while any request in the history is waiting ----
function approvalText(tool) {
  if (tool === "save_project") return ["Save the project?", "Claude wants to write the open AWR project to a file."];
  if (tool === "new_project") return ["Start a new project?", "This closes the open AWR project. Unsaved work in it is lost."];
  if (tool === "Write" || tool === "Edit") return ["Change a file outside the design folder?", "Claude wants to write to this file. Fieldnote only allows that without asking inside AWRMWO-mcp-v2, and never for .emp files."];
  if (tool === "Bash" || tool === "PowerShell") return ["Run a command?", "Claude wants to run this shell command on your PC."];
  if (tool.startsWith("delete_")) return [`Delete ${tool.slice(7).replaceAll("_", " ")}?`, "Claude wants to remove it from the AWR project."];
  return [`Run ${tool.replaceAll("_", " ")}?`, "Claude wants to run this tool."];
}
const APPROVAL_OUTCOME = { waiting: "waiting for you", allowed: "you allowed it", denied: "you denied it", expired: "no answer, so it was denied" };
let shownApproval = null;

function renderApproval(items) {
  const waiting = items.filter((it) => it.kind === "approval" && it.status === "waiting");
  const dlg = $("approval");
  dlg.hidden = !waiting.length;
  if (!waiting.length) { shownApproval = null; return; }
  const it = waiting[0];
  const [title, text] = approvalText(it.tool);
  $("apTitle").textContent = title;
  $("apText").textContent = text;
  $("apPreview").textContent = it.preview;
  $("apNote").textContent = "If you don't answer, Fieldnote denies it after 2 minutes." + (waiting.length > 1 ? ` ${waiting.length - 1} more waiting.` : "");
  dlg.dataset.id = it.id;
  if (shownApproval !== it.id) {
    shownApproval = it.id;
    $("apAllow").disabled = $("apDeny").disabled = false;
    $("apDeny").focus();  // Enter never allows by accident
  }
}

async function answerApproval(behavior) {
  $("apAllow").disabled = $("apDeny").disabled = true;
  const r = await api("answer", $("approval").dataset.id, behavior);
  if (!r.ok) { showBanner(r.error); $("apAllow").disabled = $("apDeny").disabled = false; }
}

const approvalRow = (it) => el("div", "note", `${approvalText(it.tool)[0].replace("?", "")}: ${APPROVAL_OUTCOME[it.status] || it.status}`);

function onHistory(items) {
  renderApproval(items);
  const feed = $("feed");
  const atEnd = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 60;
  feed.replaceChildren(...items.map((it) =>
    it.kind === "step" ? stepRow(it) : it.kind === "approval" ? approvalRow(it) : it.kind === "note" ? el("div", "note", it.text) : el("div", `msg ${it.kind}`, it.text)));
  feed.hidden = !items.length;
  $("feedEmpty").hidden = !!items.length;
  if (atEnd || items.length === 1) feed.scrollTop = feed.scrollHeight;
}

async function send() {
  const text = $("task").value.trim();
  if (!text) return;
  const r = await api("send", text);
  if (r.ok) $("task").value = "";
  else showBanner(r.error);
}

const projectTitle = (p) => (p.project || "AWR project").replace(/\.emp$/i, "");

function fillList(id, items, emptyText) {
  const ul = $(id);
  ul.replaceChildren();
  for (const name of items || []) ul.append(Object.assign(document.createElement("li"), { textContent: name }));
  if (!ul.children.length) ul.append(Object.assign(document.createElement("li"), { className: "none", textContent: emptyText }));
}

function renderProject(p, problem) {
  $("projectEmpty").hidden = !!p;
  $("projectCard").hidden = !p;
  if (!p) {
    $("projectEmptyText").textContent = problem || "Fieldnote shows the project that is open in AWR.";
    return;
  }
  $("projectName").textContent = projectTitle(p);
  $("projectFile").textContent = p.file && p.file !== p.project ? p.file : "Not saved to a file yet";
  $("projectSaved").textContent = p.saved ? "All changes saved in AWR" : "Unsaved changes in AWR";
  $("projectSaved").classList.toggle("unsaved", !p.saved);
  $("nSchematics").textContent = (p.schematics || []).length;
  $("nGraphs").textContent = (p.graphs || []).length;
  $("nEm").textContent = (p.em_structures || []).length;
  $("nNetlists").textContent = (p.netlists || []).length;
  fillList("listSchematics", p.schematics, "No schematics yet");
  fillList("listGraphs", p.graphs, "No graphs yet");
  fillList("listEm", p.em_structures, "No EM structures yet");
  fillList("listNetlists", p.netlists, "No netlists yet");
}

function applyTheme(theme) {
  const t = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  const next = t === "dark" ? "light" : "dark";
  $("theme").title = $("theme").ariaLabel = `Switch to ${next} theme`;
}

async function toggleTheme() {
  const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(t);
  await api("save_settings", { theme: t });
}

async function reconnect() {
  showBanner("");
  $("detail").textContent = "Reconnecting…";
  await api("reconnect");
}

let started = false;
async function startUp() {
  if (started) return;  // pywebviewready and the ready check below can both fire
  started = true;
  applyTheme((await api("settings")).theme);
  onState(await api("state"));
  onHistory(await api("history"));
}

window.fieldnote = { onState, onHistory };
$("composer").addEventListener("submit", (e) => { e.preventDefault(); send(); });
$("stop").addEventListener("click", () => api("stop_turn"));
$("apAllow").addEventListener("click", () => answerApproval("allow"));
$("apDeny").addEventListener("click", () => answerApproval("deny"));
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("approval").hidden) answerApproval("deny"); });
let clearTimer = null;  // Clear wipes the saved history: first click arms it, a second click within 4 s clears
$("clear").addEventListener("click", () => {
  const b = $("clear");
  const disarm = () => { clearTimer = null; delete b.dataset.armed; b.textContent = "Clear"; b.title = "Clear the saved history"; };
  if (!clearTimer) {
    b.dataset.armed = "1"; b.textContent = "Clear all?"; b.title = "Click again to delete the whole history";
    clearTimer = setTimeout(disarm, 4000);
    return;
  }
  clearTimeout(clearTimer);
  disarm();
  api("clear_history");
});
for (const b of document.querySelectorAll(".mode button"))
  b.addEventListener("click", () => { if (b.getAttribute("aria-pressed") !== "true") setMode(b.dataset.mode); });
$("theme").addEventListener("click", toggleTheme);
$("reconnect").addEventListener("click", reconnect);
$("bannerRetry").addEventListener("click", reconnect);
window.addEventListener("pywebviewready", startUp);
if (window.pywebview?.api?.state) startUp();
