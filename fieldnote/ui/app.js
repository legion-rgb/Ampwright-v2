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
}

// ---- chat and progress feed: every change arrives as the full history ----
const STEP_ICON = [[/graph|measurement/, "i-graph"], [/simulat|frequenc|optim|sweep|status/, "i-sim"], [/^(em_|.*_em_|.*em_structure)/, "i-em"],
                   [/schematic|element|shunt|port|ground|connect|parameter|equation/, "i-schematic"]];
const STATUS_TEXT = { running: "Running", done: "Done", failed: "Failed", stopped: "Stopped" };
const el = (tag, cls, text) => Object.assign(document.createElement(tag), { className: cls || "", textContent: text ?? "" });

function stepRow(it) {
  const row = el("div", "step");
  row.dataset.status = it.status;
  const icon = (STEP_ICON.find(([re]) => re.test(it.tool)) || [0, "i-netlist"])[1];
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
$("clear").addEventListener("click", () => api("clear_history"));
$("theme").addEventListener("click", toggleTheme);
$("reconnect").addEventListener("click", reconnect);
$("bannerRetry").addEventListener("click", reconnect);
window.addEventListener("pywebviewready", startUp);
if (window.pywebview?.api?.state) startUp();
