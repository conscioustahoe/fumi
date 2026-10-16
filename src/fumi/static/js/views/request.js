// The main area: the request editor on the left and the response on the right.
import { saveSoon } from "../branch.js";
import { draft, problems, urlHTML } from "../request.js";
import { S, authHint, curEnv, op, ops } from "../state.js";
import { $, esc } from "../util.js";
import { responseHTML } from "./response.js";

export function renderMain() {
  const o = op();
  if (!o) {
    $("#main").innerHTML = `<div class="empty">${ops().length ? "pick an endpoint" : "no endpoints yet"}</div>`;
    return;
  }
  const errs = problems(o).filter((p) => p.level === "err");
  if (!o.body && S.tab === "body") S.tab = "params";
  const tabs = [["params", "params"], ["headers", "headers"], ...(o.body ? [["body", "body"]] : [])];
  $("#main").innerHTML = `
    <div class="split">
      <div class="pane">
        <div class="pane-h">
          <div class="title-row"><h2>${esc(o.summary)}</h2><span class="sub mono">${esc(o.id)}</span></div>
          <div class="urlbar">
            <div class="urlbox"><span class="m">${esc(o.method)}</span><span id="url">${urlHTML(o)}</span></div>
            <button class="btn primary" data-act="send" ${errs.length || S.sending ? "disabled" : ""} title="${esc(errs[0]?.msg || "Send (⌘↵)")}">${S.sending ? "…" : "send"}</button>
          </div>
        </div>
        <div class="tabs">${tabs.map(([k, l]) => `<button class="tab ${S.tab === k ? "on" : ""}" data-act="tab" data-tab="${k}">${l}</button>`).join("")}</div>
        <div class="blocker" id="blocker">${esc(errs.map((p) => p.msg).join(" · "))}</div>
        <div class="tab-body">${tabHTML(o)}</div>
      </div>
      <div class="pane" id="resp">${responseHTML(o)}</div>
    </div>`;
  if (S.tab === "body" && o.body) wireEditor(o);
}

function tabHTML(o) {
  const d = draft(o);
  if (S.tab === "params") {
    const rows = o.params.filter((p) => p.in !== "header");
    if (!rows.length) return `<div class="empty">no parameters</div>`;
    return `<table class="kv">${rows.map((p) => `<tr title="${esc(p.description)}"><td>${esc(p.name)}${p.required ? '<span class="req">*</span>' : ""}</td>
      <td><input data-param="${esc(p.name)}" value="${esc(d.params[p.name] || "")}" placeholder="${esc(p.type)} · ${esc(p.in)}" spellcheck="false"></td></tr>`).join("")}</table>`;
  }
  if (S.tab === "headers") {
    const hint = authHint(curEnv());
    return `<table class="kv">
      ${hint ? `<tr class="inherited" title="from the ${esc(S.ws.env)} environment"><td>${esc(hint[0])}</td><td class="plain">${esc(hint[1])}</td></tr>` : ""}
      ${o.params.filter((p) => p.in === "header").map((p) => `<tr><td>${esc(p.name)}${p.required ? '<span class="req">*</span>' : ""}</td><td><input data-param="${esc(p.name)}" value="${esc(d.params[p.name] || "")}" placeholder="${esc(p.type)}"></td></tr>`).join("")}
      ${d.headers.map(([k, v], i) => `<tr><td><input data-hk="${i}" value="${esc(k)}" placeholder="name"></td><td><input data-hv="${i}" value="${esc(v)}" placeholder="value"></td></tr>`).join("")}
      <tr><td><button class="link" data-act="add-header">+ header</button></td><td></td></tr></table>`;
  }
  return `<div class="editor"><pre id="hl"></pre><textarea id="body-ta" spellcheck="false">${esc(d.body)}</textarea></div><div class="issues" id="issues"></div>`;
}

// Updates the send button, blocker line and URL without rebuilding the pane so the caret stays put.
export function refreshValidity(o) {
  const probs = problems(o);
  const errs = probs.filter((p) => p.level === "err");
  const send = document.querySelector('[data-act="send"]');
  if (send) { send.disabled = errs.length > 0 || S.sending; send.title = errs[0]?.msg || "Send (⌘↵)"; }
  const bl = $("#blocker");
  if (bl) bl.textContent = errs.map((p) => p.msg).join(" · ");
  const url = $("#url");
  if (url) url.innerHTML = urlHTML(o);
  return probs;
}

function hlJSON(text, unknown) {
  return esc(text)
    .replace(/(&quot;)([^&\n]*?)(&quot;)(\s*:)/g, (m, a, k, b, c) => (unknown.includes(k) ? `<mark>${a}${k}${b}</mark>${c}` : `<span class="k">${a}${k}${b}</span>${c}`))
    .replace(/(:\s*)(&quot;.*?&quot;)/g, '$1<span class="s">$2</span>')
    .replace(/(:\s*)(-?\d+\.?\d*(?:[eE][+-]?\d+)?)/g, '$1<span class="nm">$2</span>') + "\n";
}

function wireEditor(o) {
  const ta = $("#body-ta");
  const paint = () => {
    draft(o).body = ta.value;
    const probs = refreshValidity(o);
    $("#hl").innerHTML = hlJSON(ta.value, probs.filter((p) => p.field).map((p) => p.field));
    $("#issues").innerHTML = probs.filter((p) => p.level === "warn").map((p) => `<div class="issue warn">${esc(p.msg)}</div>`).join("");
  };
  ta.addEventListener("input", () => { paint(); saveSoon(); });
  ta.addEventListener("keydown", (e) => {
    if (e.key !== "Tab") return;
    e.preventDefault();
    ta.setRangeText("  ", ta.selectionStart, ta.selectionEnd, "end");
    paint();
  });
  paint();
}
