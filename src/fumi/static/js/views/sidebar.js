// Endpoints grouped by tag and named by summary.
import { S, ops } from "../state.js";
import { $, esc } from "../util.js";

export const matches = (o, q) => !q || [o.summary, o.path, o.id, o.tag].some((x) => x.toLowerCase().includes(q));

export const tagsOf = () => [...new Set(ops().map((o) => o.tag))];
export const allFolded = () => tagsOf().every((t) => S.collapsed[t]);

export function renderSidebar() {
  const q = S.filter.toLowerCase();
  const list = ops().filter((o) => matches(o, q));
  const tags = [...new Set(list.map((o) => o.tag))];
  const hadFocus = document.activeElement?.id === "filter";
  const fold = tags.length > 1 && !q ? `<button class="link fold" data-act="fold-all">${allFolded() ? "expand all" : "collapse all"}</button>` : "";
  $("#sidebar").innerHTML = `
    <div class="search"><input id="filter" placeholder="search  ⌘K" value="${esc(S.filter)}" autocomplete="off">${fold}</div>
    <div class="side-scroll">
      ${tags.map((t) => groupHTML(t, list.filter((o) => o.tag === t), q)).join("")}
      ${list.length ? "" : `<div class="quiet pad">${ops().length ? "no matches" : "no endpoints"}</div>`}
    </div>`;
  if (hadFocus) {
    const i = $("#filter");
    i.focus();
    i.setSelectionRange(i.value.length, i.value.length);
  }
}

function groupHTML(tag, group, q) {
  const fresh = group.some((o) => S.fresh.has(o.id));
  const head = `<div class="tag-row" data-act="tag" data-tag="${esc(tag)}">${esc(tag[0].toUpperCase() + tag.slice(1))}${fresh ? '<span class="new" title="New since the last read"></span>' : ""}</div>`;
  if (S.collapsed[tag] && !q) return head;
  return head + group.map((o) => `<div class="op-row ${o.id === S.opId ? "sel" : ""} ${o.deprecated ? "stale" : ""}" data-act="op" data-op="${esc(o.id)}" title="${esc(o.method)} ${esc(o.path)}">
    <span class="m ${esc(o.method)}">${esc(o.method)}</span><span class="name">${esc(o.summary)}</span></div>`).join("");
}
