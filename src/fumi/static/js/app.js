// Fumi UI entry point: actions plus delegated DOM events. Views only render and never call the server.
import { api, events } from "./api.js";
import * as branch from "./branch.js";
import { blocking, draft, toSend } from "./request.js";
import { S, curEnv, op, ops } from "./state.js";
import { $, esc, toast } from "./util.js";
import { renderDrawer } from "./views/drawer.js";
import { renderBanner, renderHeader } from "./views/header.js";
import { closeOverlay, confirmProtected, openPalette } from "./views/overlay.js";
import { refreshValidity, renderMain } from "./views/request.js";
import { allFolded, renderSidebar, tagsOf } from "./views/sidebar.js";
import { startHTML } from "./views/start.js";

const READS = ["GET", "HEAD", "OPTIONS"];

function render() {
  document.body.dataset.view = S.view;
  if (S.view === "work") {
    renderHeader(); renderBanner(); renderSidebar(); renderMain(); renderDrawer();
    return;
  }
  document.body.classList.remove("protected");
  ["#header", "#banner", "#sidebar", "#drawer"].forEach((s) => ($(s).innerHTML = ""));
  $("#main").innerHTML = S.view === "start" ? startHTML() : `<div class="empty">…</div>`;
}

// ---------- actions ----------

async function openSpec(path) {
  S.opening = true; S.openError = null; render();
  try {
    await enter(await api.open(path));
  } catch (e) {
    S.openError = e.message;
  }
  S.opening = false;
  render();
}

async function enter(ws) {
  S.ws = ws; S.view = "work"; S.opId = null; S.response = null; S.fresh = new Set();
  await branch.load(ws.branch);
  render();
}

async function closeSpec() {
  await branch.saveNow();
  await api.close();
  S.ws = null; S.branchLoaded = null; S.openError = null;
  S.session = await api.session();
  S.view = "start";
  render();
}

function pickOp(id) {
  closeOverlay();
  S.opId = id;
  S.tab = op().body ? "body" : "params";
  if (S.response?.opId !== id) S.response = null;
  renderSidebar(); renderMain();
  branch.saveSoon();
}

async function send(confirm) {
  const o = op();
  if (!o || S.sending || blocking(o).length) return;
  const env = curEnv();
  if (env.protected && !READS.includes(o.method) && confirm !== env.name) return confirmProtected(o, env, send);
  S.sending = true;
  renderMain();
  try {
    S.response = { opId: o.id, ...(await api.send({ env: env.name, confirm, ...toSend(o) })) };
  } catch (e) {
    S.response = { opId: o.id, error: e.message };
  }
  S.sending = false;
  renderMain();
  branch.saveSoon();
}

async function switchEnv(name) {
  if (!S.ws || name === S.ws.env) return;
  try { S.ws = await api.setActiveEnv(name); render(); toast(name); } catch (e) { toast(e.message); }
}

async function saveEnv(f) {
  const env = curEnv();
  const auth = { type: f.auth.value, browser: f.browser.value, header: f.header.value.trim() || "X-API-Key" };
  try {
    let ws = await api.putEnv(env.name, { base_url: f.base_url.value.trim(), protected: f.protected.checked, auth });
    if (auth.type === "api_key" && f.api_key.value.trim()) ws = await api.putSecret(env.name, "api_key", f.api_key.value.trim());
    S.ws = ws; render(); toast(`${env.name} saved`);
  } catch (e) { toast(e.message); }
}

async function addEnv(f) {
  const name = f.name.value.trim();
  try {
    await api.putEnv(name, { base_url: f.base_url.value.trim(), protected: name === "prod", auth: curEnv().auth });
    S.ws = await api.setActiveEnv(name); render(); toast(`${name} added`);
  } catch (e) { toast(e.message); }
}

async function deleteEnv() {
  const name = S.ws.env;
  if (!confirm(`Delete the ${name} environment and its saved key?`)) return;
  try { S.ws = await api.deleteEnv(name); render(); toast(`${name} deleted`); } catch (e) { toast(e.message); }
}

// A reload from disk. On a branch switch the old branch's UI state is saved and the new one's restored.
async function onSpec(e) {
  const next = e.workspace;
  const switched = S.branchLoaded && next.branch !== S.branchLoaded;
  if (switched) await branch.saveNow();
  S.ws = next;
  if (e.diff) S.fresh = new Set(e.diff.added.map((a) => a.id));
  if (switched) await branch.load(next.branch);
  else if (S.opId && !op(S.opId)) S.opId = null;
  if (!S.opId && ops().length) S.opId = ops()[0].id;
  render();
  const d = e.diff;
  if (next.error) toast(`couldn't read ${next.spec_rel}${next.git ? ` on ${next.branch}` : ""}`);
  else if (d && (d.added.length || d.removed.length)) {
    const counts = [d.added.length && `+${d.added.length}`, d.removed.length && `−${d.removed.length}`].filter(Boolean).join(" ");
    toast(`${next.git ? next.branch + " · " : ""}${counts} endpoints`);
  } else if (switched) toast(next.branch);
}

function onEvent(e) {
  if (!S.ws || S.view !== "work") return;
  if (e.type === "spec") return onSpec(e);
  if (e.type === "env") {
    S.ws = e.workspace;
    renderHeader(); renderDrawer();
    if (S.tab === "headers") renderMain();
  }
}

// ---------- DOM events ----------

const CLICKS = {
  op: (t) => pickOp(t.dataset.op),
  tag: (t) => { S.collapsed[t.dataset.tag] = !S.collapsed[t.dataset.tag]; renderSidebar(); },
  "fold-all": () => {
    const fold = !allFolded();
    S.collapsed = Object.fromEntries(tagsOf().map((t) => [t, fold]));
    renderSidebar();
  },
  tab: (t) => { S.tab = t.dataset.tab; renderMain(); branch.saveSoon(); },
  rtab: (t) => { S.respTab = t.dataset.tab; renderMain(); },
  send: () => send(),
  toggle: (t) => t.parentElement.classList.toggle("collapsed"),
  drawer: () => { S.drawerOpen = !S.drawerOpen; renderDrawer(); },
  "drawer-open": () => { S.drawerOpen = true; renderDrawer(); },
  "pick-env": (t) => switchEnv(t.dataset.env),
  "delete-env": () => deleteEnv(),
  close: () => closeOverlay(),
  "add-header": () => { draft(op()).headers.push(["", ""]); renderMain(); },
  "open-recent": (t) => openSpec(t.dataset.path),
  "clear-recent": async () => {
    try { S.session.recent = (await api.clearRecent()).recent; render(); } catch (e) { toast(e.message); }
  },
  "close-spec": () => closeSpec(),
  reload: () => api.reload().catch((err) => toast(err.message)),
};

document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-act]");
  if (!t) { if (e.target.id === "overlay") closeOverlay(); return; }
  CLICKS[t.dataset.act]?.(t);
});

document.addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.target;
  if (f.dataset.form === "open") return f.path.value.trim() && openSpec(f.path.value.trim());
  if (f.dataset.form === "env") return saveEnv(f);
  if (f.dataset.form === "new-env") return addEnv(f);
});

document.addEventListener("change", (e) => {
  const t = e.target;
  if (t.dataset.act === "env") return switchEnv(t.value);
  if (t.name === "auth" && t.closest('form[data-form="env"]')) {
    t.form.querySelectorAll("[data-show]").forEach((el) => el.classList.toggle("hidden", el.dataset.show !== t.value));
  }
});

document.addEventListener("input", (e) => {
  const t = e.target;
  if (t.id === "filter") { S.filter = t.value; return renderSidebar(); }
  const o = op();
  if (!o || t.closest("#drawer")) return;
  const d = draft(o);
  if (t.dataset.param !== undefined) d.params[t.dataset.param] = t.value;
  else if (t.dataset.hk !== undefined) d.headers[+t.dataset.hk][0] = t.value;
  else if (t.dataset.hv !== undefined) d.headers[+t.dataset.hv][1] = t.value;
  else return;
  refreshValidity(o);
  branch.saveSoon();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeOverlay();
  if (!(e.metaKey || e.ctrlKey) || S.view !== "work") return;
  if (e.key === "Enter") { e.preventDefault(); send(); }
  if (e.key === "k") { e.preventDefault(); openPalette(pickOp); }
  if (e.key === "e") {
    e.preventDefault();
    const names = S.ws.envs.map((x) => x.name);
    switchEnv(names[(names.indexOf(S.ws.env) + 1) % names.length]);
  }
});

window.addEventListener("beforeunload", () => branch.saveNow());

// ---------- start ----------

async function boot() {
  try {
    S.session = await api.session();
  } catch (e) {
    $("#main").innerHTML = `<div class="empty"><span class="bad">Can't reach fumi: ${esc(e.message)}</span></div>`;
    return;
  }
  events(onEvent);
  if (S.session.workspace) return enter(S.session.workspace);
  S.view = "start";
  render();
}

boot();
