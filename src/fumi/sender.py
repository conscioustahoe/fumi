"""Sending a request to the service. Never retries."""

import json
import time
from http.cookies import SimpleCookie

import httpx

MAX_BODY = 2 * 1024 * 1024
TIMEOUT = 30


def _cookies(resp: httpx.Response) -> list[dict]:
    out = []
    for raw in resp.headers.get_list("set-cookie"):
        jar = SimpleCookie()
        try:
            jar.load(raw)
        except Exception:
            continue
        for name, morsel in jar.items():
            out.append({
                "name": name,
                "domain": morsel["domain"] or resp.url.host,
                "path": morsel["path"] or "/",
                "expires": morsel["expires"] or (f"max-age {morsel['max-age']}s" if morsel["max-age"] else "session"),
            })
    return out


async def send(base_url: str, method: str, path: str, query: list, headers: list, body: str | None) -> dict:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    hdrs = {k: v for k, v in headers if k}
    content = None
    if body is not None and body.strip() and method not in ("GET", "HEAD"):
        content = body.encode()
        if not any(k.lower() == "content-type" for k in hdrs):
            hdrs["Content-Type"] = "application/json"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
            resp = await client.request(method, url, params=[(k, v) for k, v in query if k], headers=hdrs, content=content)
            raw = await resp.aread()
    except httpx.ConnectError:
        return {"error": f"Can't reach {base_url}. Is the service running?"}
    except httpx.TimeoutException:
        return {"error": f"No response from {url} after {TIMEOUT}s"}
    except httpx.HTTPError as e:
        return {"error": f"{type(e).__name__}: {e}"}
    ms = round((time.perf_counter() - started) * 1000)

    text = raw[:MAX_BODY].decode(errors="replace")
    parsed = None
    if "json" in resp.headers.get("content-type", ""):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
    return {
        "status": resp.status_code,
        "reason": resp.reason_phrase,
        "ms": ms,
        "size": len(raw),
        "truncated": len(raw) > MAX_BODY,
        "url": str(resp.request.url),
        "headers": [[k, v] for k, v in resp.headers.multi_items()],
        "cookies": _cookies(resp),
        "json": parsed,
        "text": None if parsed is not None else text,
    }
