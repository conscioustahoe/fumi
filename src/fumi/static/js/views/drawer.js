// The environment drawer at the bottom: list on the left and the open environment's settings on the right.
import { S, browserLabel, curEnv } from "../state.js";
import { $, esc } from "../util.js";

const host = (url) => url.replace(/^https?:\/\//, "");

export function renderDrawer() {
  const env = curEnv();
  $("#drawer").innerHTML = `
    <div class="drawer-h" data-act="drawer"><span>environment</span><span class="quiet">${esc(env.name)}${env.protected ? " · protected" : ""}</span><span class="spacer"></span><span class="quiet">${S.drawerOpen ? "−" : "+"}</span></div>
    ${S.drawerOpen ? `<div class="drawer-body envs">${listHTML(env)}${formHTML(env)}</div>` : ""}`;
}

function listHTML(env) {
  return `<div class="drawer-col">
    <h4>environments</h4>
    ${S.ws.envs.map((e) => `<div class="env-row ${e.name === env.name ? "sel" : ""}" data-act="pick-env" data-env="${esc(e.name)}"><span>${esc(e.name)}</span><span class="quiet mono">${esc(host(e.base_url))}</span></div>`).join("")}
    <form data-form="new-env" class="row new-env"><input class="line" name="name" placeholder="name" spellcheck="false"><input class="line mono" name="base_url" placeholder="https://api.example.com" spellcheck="false"><button class="link">add</button></form>
  </div>`;
}

function formHTML(env) {
  const a = env.auth || { type: "none" };
  const show = (type) => (a.type === type ? "" : "hidden");
  const opt = (value, label, current) => `<option value="${value}" ${current === value ? "selected" : ""}>${label}</option>`;
  return `<form class="drawer-col" data-form="env">
    <h4>${esc(env.name)} ${S.ws.envs.length > 1 ? `<button type="button" class="link" data-act="delete-env">delete</button>` : ""}</h4>
    <label class="field"><span>base url</span><input class="line mono" name="base_url" value="${esc(env.base_url)}" spellcheck="false"></label>
    <label class="field"><span>sign in with</span><select name="auth">
      ${opt("none", "nothing", a.type)}${opt("browser", "my browser session", a.type)}${opt("api_key", "an API key", a.type)}</select></label>
    <label class="field ${show("browser")}" data-show="browser"><span>browser</span><select name="browser">
      ${["brave", "chrome", "arc", "edge"].map((b) => opt(b, browserLabel(b), a.browser || "brave")).join("")}</select></label>
    <label class="field ${show("api_key")}" data-show="api_key"><span>header</span><input class="line mono" name="header" value="${esc(a.header || "X-API-Key")}"></label>
    <label class="field ${show("api_key")}" data-show="api_key"><span>key</span><input class="line mono" type="password" name="api_key" autocomplete="off" placeholder="${env.secrets.includes("api_key") ? "saved · type to replace" : "paste the key"}"></label>
    <label class="field check"><input type="checkbox" name="protected" ${env.protected ? "checked" : ""}><span>protected: type the name before any write</span></label>
    <div class="actions left"><button class="btn primary">save</button></div>
    <p class="quiet small ${show("browser")}" data-show="browser">Sign in through your web app in that browser. Fumi reads its cookies for this host when you send and never saves them. macOS asks once for permission.</p>
    <p class="quiet small">Kept in ~/.fumi on this Mac and never next to the spec. Keys are write-only here.</p>
  </form>`;
}
