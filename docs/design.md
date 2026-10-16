# Design

## Rules

- **Read the spec and nothing else.** Fumi never starts or imports the service. The OpenAPI file is the contract.
- **One address.** The server listens on 127.0.0.1:3737. No dynamic ports and no other hosts.
- **Your data stays yours.** Environments and keys and UI state live in `~/.fumi`. Nothing is written next to the spec or into its repo.
- **A broken spec never blanks the screen.** You keep the last good copy and see the error.
- **Untrusted by default.** Spec text and responses reach the page only through one escaping helper.
- **Small modules with one job each.** Routes stay thin. Logic lives in plain modules that are easy to test.

## Server

Python with FastAPI and uvicorn. It reads the spec and watches it and sends requests with httpx. The browser never calls the target API directly.

| Module | Job |
|---|---|
| `cli.py` | The `fumi` command. Fixed host and port |
| `server.py` | HTTP routes. Validates input and hands off |
| `security.py` | Loopback host and origin checks |
| `spec.py` | Reads an OpenAPI file from disk and says why when it can't |
| `openapi.py` | Flattens a spec into the operations the UI lists and diffs two of them |
| `workspace.py` | The open spec: reload and watch the file and git HEAD |
| `gitinfo.py` | Read-only git queries |
| `envs.py` | Environments and the protected write rule |
| `auth.py` | Signs a request with a browser session or an API key |
| `browser_cookies.py` | Reads a Chromium browser's cookies for one host at send time |
| `sender.py` | Sends one request. Never retries |
| `events.py` | Pushes changes to open tabs over server-sent events |
| `store.py` | Files in `~/.fumi`. Atomic writes with mode 600 |

## Security

No token and no link to paste. The server answers only Fumi's own page:

- The Host header must be a loopback name so a web page can't reach Fumi through DNS rebinding.
- A request from another site's page carries that site's Origin and Fumi refuses it.
- Every API call carries an `X-Fumi` header. Another site can't add a custom header without a CORS preflight and Fumi answers no preflight.

Secret values never leave the server. The UI sees only their names.

## UI

Plain HTML and CSS and JavaScript served as native ES modules. No Node and no build step.

| File | Job |
|---|---|
| `js/app.js` | Entry point. Actions and DOM events |
| `js/state.js` | The one state object and shared lookups |
| `js/request.js` | The draft being edited and what blocks sending it |
| `js/branch.js` | Saving and restoring UI state per branch |
| `js/api.js` | Calls to the local server |
| `js/views/*.js` | One file per screen region. Views render and never call the server |
