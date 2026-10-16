// The top bar and the banner that shows when the spec can't be read.
import { S, curEnv } from "../state.js";
import { $, esc } from "../util.js";

export function renderHeader() {
  const w = S.ws;
  const where = w.git ? `${esc(w.name)}<span class="quiet">/</span>${esc(w.branch)}` : esc(w.name);
  const status = w.error ? '<span class="bad">spec failed</span>' : w.sha ? esc(w.sha) : "";
  const read = w.loaded_at ? `${w.spec_rel} read at ${new Date(w.loaded_at * 1000).toLocaleTimeString()}` : "";
  $("#header").innerHTML = `
    <div class="logo">fumi</div>
    <button class="crumb" data-act="close-spec" title="Open another spec">${where}</button>
    <span class="quiet mono" title="${esc(read)}">${status}</span>
    <button class="icon" data-act="reload" title="Read the spec again">↻</button>
    <div class="spacer"></div>
    <button class="link" data-act="drawer" title="Edit environments">${esc(w.base_url.replace(/^https?:\/\//, ""))}</button>
    <select class="env" data-act="env" title="Environment (⌘E)">
      ${w.envs.map((e) => `<option value="${esc(e.name)}" ${e.name === w.env ? "selected" : ""}>${esc(e.name)}</option>`).join("")}
    </select>`;
  document.body.classList.toggle("protected", !!curEnv()?.protected);
}

export function renderBanner() {
  const w = S.ws;
  if (!w.error) return ($("#banner").innerHTML = "");
  const at = w.git ? ` on ${esc(w.branch)} @ ${esc(w.sha)}` : "";
  const good = w.good ? `Showing the last good copy${w.good.branch !== "-" ? ` from ${esc(w.good.branch)}` : ""}.` : "Nothing to show yet.";
  $("#banner").innerHTML = `<details class="banner" ${w.good ? "" : "open"}><summary>Couldn't read ${esc(w.spec_rel)}${at}. ${good}
    <button class="link" data-act="reload">retry</button></summary><pre>${esc(w.error)}</pre></details>`;
}
