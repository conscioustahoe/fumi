// The response pane: status line then body as a foldable JSON tree plus headers and cookies.
import { S } from "../state.js";
import { esc, fmtSize } from "../util.js";

const TABS = [["body", "body"], ["headers", "headers"], ["cookies", "cookies"]];

export function responseHTML(o) {
  const r = S.response && S.response.opId === o.id ? S.response : null;
  if (S.sending) return `<div class="empty">sending…</div>`;
  if (!r) return `<div class="empty">⌘↵ to send</div>`;
  if (r.error) {
    const fix = r.auth_error ? `<p><button class="link" data-act="drawer-open">environment settings</button></p>` : "";
    return `<div class="empty"><span class="bad">${esc(r.error)}</span>${fix}</div>`;
  }
  return `<div class="pane-h"><div class="resp-meta">
      <span class="status s${String(r.status)[0]}">${r.status}</span><span class="quiet">${esc(r.reason)}</span>
      <span class="quiet">${r.ms} ms · ${fmtSize(r.size)}${r.truncated ? " · truncated" : ""}</span>
      <span class="spacer"></span>${sentWith(r)}
    </div></div>
    <div class="tabs">${TABS.map(([k, l]) => `<button class="tab ${S.respTab === k ? "on" : ""}" data-act="rtab" data-tab="${k}">${l}</button>`).join("")}</div>
    <div class="tab-body">${tabHTML(r)}</div>`;
}

function sentWith(r) {
  const a = r.auth;
  const title = a ? `${a.kind === "cookies" ? "cookies" : "key"} from ${a.from}: ${a.names.join(", ")}` : "no credentials sent";
  const label = a ? ` · ${a.kind === "cookies" ? a.from.split(" ")[0] + " session" : "api key"}` : "";
  return `<span class="quiet" title="${esc(title)}">${esc(r.env || "")}${esc(label)}</span>`;
}

function tabHTML(r) {
  if (S.respTab === "headers") return `<table class="kv">${r.headers.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")}</table>`;
  if (S.respTab === "cookies") {
    if (!r.cookies.length) return `<div class="empty">none</div>`;
    return `<table class="kv">${r.cookies.map((c) => `<tr><td>${esc(c.name)}</td><td class="plain">${esc(c.domain)}${esc(c.path)} · ${esc(c.expires)}</td></tr>`).join("")}</table>`;
  }
  if (r.json !== null && r.json !== undefined) return `<div class="json">${jsonTree(r.json, null, true)}</div>`;
  return r.text ? `<pre class="raw">${esc(r.text)}</pre>` : `<div class="empty">empty body</div>`;
}

function jsonTree(v, key, last) {
  const k = key === null || typeof key === "number" ? "" : `<span class="k">"${esc(key)}"</span>: `;
  const comma = last ? "" : ",";
  if (v && typeof v === "object") {
    const arr = Array.isArray(v);
    const entries = arr ? v.map((x, i) => [i, x]) : Object.entries(v);
    const [open, close] = arr ? ["[", "]"] : ["{", "}"];
    if (!entries.length) return `<div class="line">${k}${open}${close}${comma}</div>`;
    const kids = entries.map(([ck, cv], i) => jsonTree(cv, ck, i === entries.length - 1)).join("");
    return `<div class="node"><span class="caret" data-act="toggle">▾</span>${k}${open}<span class="ellipsis"> … ${entries.length} ${arr ? "items" : "keys"} ${close}${comma}</span><div class="children">${kids}</div><span class="close">${close}${comma}</span></div>`;
  }
  const cls = typeof v === "string" ? "s" : typeof v === "number" ? "n" : "b";
  const shown = typeof v === "string" ? `"${esc(v)}"` : esc(JSON.stringify(v));
  return `<div class="line">${k}<span class="leaf ${cls}">${shown}</span>${comma}</div>`;
}
