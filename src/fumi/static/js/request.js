// The request being edited: its draft, what blocks sending it and the URL it will hit.
import { S } from "./state.js";
import { esc } from "./util.js";

export function draft(o) {
  if (!S.drafts[o.id]) {
    const params = {};
    o.params.forEach((p) => { if (p.example !== null && p.example !== undefined && p.in !== "path") params[p.name] = String(p.example); });
    S.drafts[o.id] = {
      params,
      headers: [],
      body: o.body ? (o.body.example === null ? "" : JSON.stringify(o.body.example, null, 2)) : "",
    };
  }
  return S.drafts[o.id];
}

// Errors block the send. Warnings only point things out.
export function problems(o) {
  const d = draft(o);
  const out = [];
  o.params.filter((p) => p.required && !(d.params[p.name] || "").trim())
    .forEach((p) => out.push({ level: "err", msg: `${p.in} parameter "${p.name}" is required` }));
  if (!o.body) return out;
  const text = d.body.trim();
  if (!text) {
    if (o.body.required) out.push({ level: "err", msg: "Body is required" });
    return out;
  }
  let parsed;
  try { parsed = JSON.parse(text); } catch (e) { out.push({ level: "err", msg: `Body is not valid JSON: ${e.message}` }); }
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed) && o.body.media.includes("json")) {
    Object.entries(o.body.fields).filter(([k, f]) => f.required && !(k in parsed))
      .forEach(([k]) => out.push({ level: "err", msg: `Missing required field "${k}"` }));
    if (!o.body.open) {
      Object.keys(parsed).filter((k) => !(k in o.body.fields))
        .forEach((k) => out.push({ level: "warn", msg: `Unknown field "${k}" (not in the spec)`, field: k }));
    }
  }
  return out;
}

export const blocking = (o) => problems(o).filter((p) => p.level === "err");

export function urlParts(o) {
  const d = draft(o);
  const path = o.path.replace(/\{(\w+)\}/g, (m, name) => {
    const v = (d.params[name] || "").trim();
    return v ? encodeURIComponent(v) : m;
  });
  const query = o.params.filter((p) => p.in === "query" && (d.params[p.name] || "") !== "").map((p) => [p.name, d.params[p.name]]);
  return { path, query };
}

export function urlHTML(o) {
  const d = draft(o);
  const { query } = urlParts(o);
  const path = esc(o.path).replace(/\{(\w+)\}/g, (m, name) => {
    const v = (d.params[name] || "").trim();
    return v
      ? `<span class="var" title="path parameter ${esc(name)}">${esc(v)}</span>`
      : `<span class="var unres" title="fill in ${esc(name)} in params">{${esc(name)}}</span>`;
  });
  const qs = query.length ? "?" + query.map(([k, v]) => `${esc(k)}=${esc(v)}`).join("&amp;") : "";
  return `<span class="quiet">${esc(S.ws.base_url)}</span>${path}${qs}`;
}

// What the server needs to send this request.
export function toSend(o) {
  const d = draft(o);
  const { path, query } = urlParts(o);
  const headers = [
    ...o.params.filter((p) => p.in === "header" && d.params[p.name]).map((p) => [p.name, d.params[p.name]]),
    ...d.headers.filter(([k]) => k.trim()),
  ];
  return { method: o.method, path, query, headers, body: o.body ? d.body : null };
}
