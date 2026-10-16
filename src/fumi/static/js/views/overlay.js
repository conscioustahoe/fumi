// Modals: the ⌘K palette and the protected-environment confirmation.
import { urlParts } from "../request.js";
import { ops } from "../state.js";
import { $, esc } from "../util.js";
import { matches } from "./sidebar.js";

function show(html) {
  $("#overlay").innerHTML = html;
  $("#overlay").classList.add("on");
}

export function closeOverlay() {
  $("#overlay").classList.remove("on");
  $("#overlay").innerHTML = "";
}

export function openPalette(onPick) {
  show(`<div class="modal palette"><input id="pal-in" placeholder="jump to…" autocomplete="off"><div class="list" id="pal-list"></div></div>`);
  const input = $("#pal-in");
  let sel = 0;
  let items = [];
  const draw = () => {
    items = ops().filter((o) => matches(o, input.value.toLowerCase()));
    sel = Math.min(sel, Math.max(items.length - 1, 0));
    $("#pal-list").innerHTML = items.map((o, n) => `<div class="item ${n === sel ? "on" : ""}" data-act="op" data-op="${esc(o.id)}"><span class="m ${esc(o.method)}">${esc(o.method)}</span><span>${esc(o.summary)}</span><span class="op mono">${esc(o.path)}</span></div>`).join("");
  };
  input.addEventListener("input", () => { sel = 0; draw(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, items.length - 1); draw(); e.preventDefault(); }
    if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); draw(); e.preventDefault(); }
    if (e.key === "Enter" && items[sel]) onPick(items[sel].id);
  });
  draw();
  input.focus();
}

// Calls onConfirm only after the user types the environment's name.
export function confirmProtected(o, env, onConfirm) {
  show(`<div class="modal danger"><div class="mh"><span class="m ${esc(o.method)}">${esc(o.method)}</span> ${esc(o.summary)} on ${esc(env.name)}</div>
    <div class="mb"><p class="quiet">${esc(env.base_url)}${esc(urlParts(o).path)}</p><p class="quiet">type <b>${esc(env.name)}</b> to send</p><input class="big" id="confirm-in" autocomplete="off" spellcheck="false"></div>
    <div class="mf"><button class="link" data-act="close">cancel</button><button class="btn primary" id="confirm-go" disabled>send</button></div></div>`);
  const input = $("#confirm-in");
  const go = $("#confirm-go");
  input.focus();
  input.addEventListener("input", () => (go.disabled = input.value !== env.name));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !go.disabled) go.click(); });
  go.addEventListener("click", () => { closeOverlay(); onConfirm(env.name); });
}
