"""Who may talk to the local server. Only Fumi's own page on a loopback address.

There is no token to paste. Three checks keep other sites out:
- The Host header must be a loopback name so a page can't reach Fumi through DNS rebinding.
- An Origin header when present must be Fumi's own so another site's scripts are refused.
- Every API call except the event stream must carry X-Fumi. Browsers never let another site
  add a custom header without a CORS preflight and Fumi answers no preflight.
"""

from fastapi import HTTPException, Request

HEADER = "x-fumi"
LOOPBACK = ("127.0.0.1", "localhost", "[::1]")


def _host(value: str) -> str:
    return value.rsplit(":", 1)[0] if not value.endswith("]") else value


def check(request: Request) -> None:
    host = request.headers.get("host") or ""
    if _host(host) not in LOOPBACK:
        raise HTTPException(403, "fumi only answers on 127.0.0.1")
    origin = request.headers.get("origin")
    if origin and origin not in (f"http://{host}", f"https://{host}"):
        raise HTTPException(403, "fumi only answers its own page")
    # EventSource can't send headers. A foreign page still can't read the stream since it gets no CORS headers.
    if request.url.path != "/api/events" and request.headers.get(HEADER) != "1":
        raise HTTPException(403, "missing X-Fumi header")
