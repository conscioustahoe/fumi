"""Signing a request in the way its environment says: a browser session or an API key or nothing."""

import asyncio
from dataclasses import dataclass

from fumi import browser_cookies, store


class AuthError(Exception):
    pass


@dataclass
class Credentials:
    headers: list[tuple[str, str]]
    applied: dict | None  # what the response view says was sent. Never the values.


async def for_request(key: str, env: dict, url: str, headers: list[tuple[str, str]]) -> Credentials:
    """Headers to add. A header the user typed by hand always wins."""
    auth = env.get("auth") or {"type": "none"}
    have = {k.lower() for k, _ in headers}

    if auth["type"] == "browser" and "cookie" not in have:
        try:
            found = await asyncio.to_thread(browser_cookies.cookies_for, url, auth.get("browser", "brave"))
        except browser_cookies.BrowserCookieError as e:
            raise AuthError(str(e))
        return Credentials([("Cookie", found.header)],
                           {"kind": "cookies", "from": f"{found.browser} ({found.profile})", "names": found.names})

    header = auth.get("header") or "X-API-Key"
    if auth["type"] == "api_key" and header.lower() not in have:
        value = store.secrets(key, env["name"]).get("api_key")
        if not value:
            raise AuthError(f"No API key saved for {env['name']}. Add one in the environment drawer.")
        return Credentials([(header, value)], {"kind": "api_key", "from": "~/.fumi secrets", "names": [header]})

    return Credentials([], None)
