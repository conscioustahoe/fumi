// UI state per git branch: the open endpoint, unsaved edits and the last response. Saved in ~/.fumi.
import { api } from "./api.js";
import { S, op, ops } from "./state.js";

const SAVE_DELAY_MS = 600;
const MAX_RESPONSE_CHARS = 300_000;
let timer = null;

function payload() {
  const resp = S.response && JSON.stringify(S.response).length < MAX_RESPONSE_CHARS ? S.response : null;
  return { opId: S.opId, tab: S.tab, drafts: S.drafts, response: resp };
}

export function saveNow(branch = S.branchLoaded) {
  clearTimeout(timer);
  if (!branch) return Promise.resolve();
  return api.saveBranchState(branch, payload()).catch(() => {});
}

export function saveSoon() {
  if (!S.ws || !S.branchLoaded) return;
  clearTimeout(timer);
  const branch = S.branchLoaded;
  timer = setTimeout(() => saveNow(branch), SAVE_DELAY_MS);
}

export async function load(branch) {
  const st = await api.branchState(branch).catch(() => ({}));
  S.branchLoaded = branch;
  S.drafts = st.drafts || {};
  S.opId = st.opId && op(st.opId) ? st.opId : S.opId && op(S.opId) ? S.opId : ops()[0]?.id || null;
  S.tab = st.tab || S.tab;
  S.response = st.response && st.response.opId === S.opId ? st.response : null;
}
