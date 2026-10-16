"""Borrow the user's signed-in session from a Chromium browser on macOS, at send time.

Cookies are read for the one request's host, used for that request, and never written anywhere.
Decrypting needs the browser's "Safe Storage" key from the macOS Keychain, so the first read makes
macOS ask the user for permission.
"""

import hashlib
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SUPPORT = Path.home() / "Library" / "Application Support"

# name -> (profile root, Keychain service, Keychain account)
BROWSERS = {
    "brave": (SUPPORT / "BraveSoftware" / "Brave-Browser", "Brave Safe Storage", "Brave"),
    "chrome": (SUPPORT / "Google" / "Chrome", "Chrome Safe Storage", "Chrome"),
    "arc": (SUPPORT / "Arc" / "User Data", "Arc Safe Storage", "Arc"),
    "edge": (SUPPORT / "Microsoft Edge", "Microsoft Edge Safe Storage", "Microsoft Edge"),
}
LABELS = {"brave": "Brave", "chrome": "Chrome", "arc": "Arc", "edge": "Edge"}
CHROMIUM_EPOCH_OFFSET = 11644473600  # seconds between 1601-01-01 and 1970-01-01
KEY_CACHE_SECS = 3600


class BrowserCookieError(Exception):
    pass


@dataclass
class Found:
    header: str  # value for the Cookie header
    names: list[str]
    browser: str
    profile: str


_keys: dict[str, tuple[bytes, float]] = {}


def keychain_password(service: str, account: str) -> bytes:
    out = subprocess.run(["security", "find-generic-password", "-w", "-s", service, "-a", account],
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise BrowserCookieError(
            f"macOS didn't give fumi the \"{service}\" key. Allow it when macOS asks, then send again.")
    return out.stdout.strip().encode()


def _key(browser: str, password_fn) -> bytes:
    cached = _keys.get(browser)
    if cached and time.time() - cached[1] < KEY_CACHE_SECS:
        return cached[0]
    _, service, account = BROWSERS[browser]
    key = hashlib.pbkdf2_hmac("sha1", password_fn(service, account), b"saltysalt", 1003, 16)
    _keys[browser] = (key, time.time())
    return key


def decrypt(encrypted: bytes, key: bytes, host_key: str, db_version: int) -> str:
    if not encrypted.startswith((b"v10", b"v11")):
        raise ValueError("unknown cookie encryption")
    dec = Cipher(algorithms.AES(key), modes.CBC(b" " * 16)).decryptor()
    raw = dec.update(encrypted[3:]) + dec.finalize()
    raw = raw[: -raw[-1]]  # PKCS#7 padding
    if db_version >= 24 and raw[:32] == hashlib.sha256(host_key.encode()).digest():
        raw = raw[32:]  # newer Chromium prefixes the value with a hash of the cookie's domain
    return raw.decode()


def domain_matches(host: str, host_key: str) -> bool:
    if host_key.startswith("."):
        base = host_key[1:]
        return host == base or host.endswith("." + base)
    return host == host_key


def path_matches(req_path: str, cookie_path: str) -> bool:
    if not cookie_path or cookie_path == "/":
        return True
    return req_path == cookie_path or req_path.startswith(cookie_path.rstrip("/") + "/")


def _profiles(root: Path) -> list[Path]:
    dirs = [root / "Default", *sorted(root.glob("Profile *"))]
    dbs = []
    for d in dirs:
        for rel in ("Network/Cookies", "Cookies"):
            if (d / rel).is_file():
                dbs.append(d / rel)
                break
    return dbs


def _read(db: Path, host: str) -> tuple[list[tuple], int]:
    # immutable=1 reads the file as-is without taking locks, so a running browser isn't disturbed.
    conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    try:
        version = 0
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'version'").fetchone()
            version = int(row[0]) if row else 0
        except sqlite3.DatabaseError:
            pass
        parts = host.split(".")
        candidates = {host, "." + host, *("." + ".".join(parts[i:]) for i in range(1, len(parts) - 1))}
        marks = ",".join("?" * len(candidates))
        rows = conn.execute(
            f"SELECT host_key, name, value, encrypted_value, path, expires_utc, is_secure FROM cookies WHERE host_key IN ({marks})",
            tuple(candidates),
        ).fetchall()
        return rows, version
    finally:
        conn.close()


def cookies_for(url: str, browser: str = "brave", password_fn=keychain_password, root: Path | None = None) -> Found:
    if browser not in BROWSERS:
        raise BrowserCookieError(f"Unknown browser {browser!r}")
    label = LABELS[browser]
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    secure_ok = parts.scheme == "https" or host in ("localhost", "127.0.0.1", "[::1]")
    root = root or BROWSERS[browser][0]
    dbs = _profiles(root)
    if not dbs:
        raise BrowserCookieError(f"Couldn't find {label}'s cookies on this Mac.")

    now = time.time()
    for db in dbs:
        try:
            rows, version = _read(db, host)
        except sqlite3.DatabaseError as e:
            raise BrowserCookieError(f"Couldn't read {label}'s cookies: {e}")
        picked: dict[str, tuple[int, str]] = {}  # name -> (specificity, value): the most specific path wins
        for host_key, name, value, encrypted, cpath, expires_utc, is_secure in rows:
            if not domain_matches(host, host_key) or not path_matches(path, cpath):
                continue
            if is_secure and not secure_ok:
                continue
            if expires_utc and expires_utc / 1_000_000 - CHROMIUM_EPOCH_OFFSET < now:
                continue
            if not value and encrypted:
                try:
                    value = decrypt(encrypted, _key(browser, password_fn), host_key, version)
                except BrowserCookieError:
                    raise
                except Exception:
                    raise BrowserCookieError(f"Couldn't decrypt {label}'s cookies (did {label} change its key?).")
            if name not in picked or len(cpath or "") > picked[name][0]:
                picked[name] = (len(cpath or ""), value)
        if picked:
            return Found(
                header="; ".join(f"{n}={v}" for n, (_, v) in picked.items()),
                names=sorted(picked),
                browser=label,
                profile=db.parent.name if db.parent.name != "Network" else db.parent.parent.name,
            )
    raise BrowserCookieError(f"You're not signed in to {host} in {label}. Sign in through the web app, then send again.")
