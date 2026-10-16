// Talking to the local fumi server. Every call carries X-Fumi so the server knows it is Fumi's own page.

export class ApiError extends Error {}

async function call(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: {
      "X-Fumi": "1",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new ApiError(typeof data.detail === "string" ? data.detail : `${res.status} ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

const q = encodeURIComponent;

export const api = {
  session: () => call("GET", "/api/session"),
  clearRecent: () => call("DELETE", "/api/recent"),
  open: (path) => call("POST", "/api/open", { path }),
  close: () => call("POST", "/api/close", {}),
  reload: () => call("POST", "/api/reload", {}),
  setActiveEnv: (name) => call("PUT", "/api/env/active", { name }),
  putEnv: (name, env) => call("PUT", `/api/envs/${q(name)}`, env),
  deleteEnv: (name) => call("DELETE", `/api/envs/${q(name)}`),
  putSecret: (env, key, value) => call("PUT", `/api/envs/${q(env)}/secrets/${q(key)}`, { value }),
  branchState: (branch) => call("GET", `/api/branch-state?branch=${q(branch)}`),
  saveBranchState: (branch, data) => call("PUT", `/api/branch-state?branch=${q(branch)}`, data),
  send: (req) => call("POST", "/api/send", req),
};

export function events(onEvent) {
  const es = new EventSource("/api/events");
  es.onmessage = (e) => onEvent(JSON.parse(e.data));
  return es;
}
