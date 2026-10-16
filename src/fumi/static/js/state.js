// The one state object and the lookups every view shares.

export const S = {
  view: "loading", // loading | start | work
  session: null,
  openError: null,
  opening: false,
  ws: null,
  opId: null,
  tab: "body",
  respTab: "body",
  filter: "",
  collapsed: {},
  drafts: {}, // opId -> { params: {name: value}, headers: [[k, v]], body: string }
  response: null, // { opId, ...result } for the open endpoint
  sending: false,
  drawerOpen: false,
  fresh: new Set(), // op ids the last reload added
  branchLoaded: null, // branch whose UI state is in S.drafts
};

export const ops = () => (S.ws ? S.ws.ops : []);
export const op = (id = S.opId) => ops().find((o) => o.id === id);
export const curEnv = () => S.ws?.envs.find((e) => e.name === S.ws.env);

const BROWSERS = { brave: "Brave", chrome: "Chrome", arc: "Arc", edge: "Edge" };
export const browserLabel = (b) => BROWSERS[b] || b;

// [header name, what fills it] for the open environment or null when it signs nothing.
export function authHint(env) {
  const a = env?.auth || { type: "none" };
  if (a.type === "browser") return ["Cookie", `your ${browserLabel(a.browser)} session read at send time`];
  if (a.type === "api_key") return [a.header || "X-API-Key", env.secrets.includes("api_key") ? "saved key ••••" : "no key saved yet"];
  return null;
}
