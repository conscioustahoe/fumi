// The screen before a spec is open: type a file path or pick a recent one.
import { S } from "../state.js";
import { esc } from "../util.js";

export function startHTML() {
  const recent = (S.session?.recent || []).slice(0, 6);
  return `<div class="start">
    <div class="start-logo">fumi</div>
    <p class="quiet">Open an OpenAPI JSON file to see its API.</p>
    <form class="open-path" data-form="open"><input name="path" placeholder="~/Workspace/service/openapi.json" autocomplete="off" spellcheck="false"><button class="btn primary" ${S.opening ? "disabled" : ""}>${S.opening ? "opening…" : "open"}</button></form>
    ${S.openError ? `<div class="issue err">${esc(S.openError)}</div>` : ""}
    ${recent.length ? `<h4 class="row-h">recent<button class="link" data-act="clear-recent">clear</button></h4>${recent.map((r) => `<div class="repo-row" data-act="open-recent" data-path="${esc(r.path)}"><span>${esc(r.name)}</span><span class="quiet mono">${esc(r.path)}</span></div>`).join("")}` : ""}
  </div>`;
}

