"""Uses a fake Chromium cookie database and a fake Keychain password; never touches a real browser."""

import hashlib
import sqlite3
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from fumi import browser_cookies as bc

PASSWORD = b"fake-keychain-password"
EPOCH = bc.CHROMIUM_EPOCH_OFFSET


def encrypt(value: str, host_key: str, version: int) -> bytes:
    key = hashlib.pbkdf2_hmac("sha1", PASSWORD, b"saltysalt", 1003, 16)
    raw = value.encode()
    if version >= 24:
        raw = hashlib.sha256(host_key.encode()).digest() + raw
    pad = 16 - len(raw) % 16
    raw += bytes([pad]) * pad
    enc = Cipher(algorithms.AES(key), modes.CBC(b" " * 16)).encryptor()
    return b"v10" + enc.update(raw) + enc.finalize()


def make_db(root: Path, rows: list[dict], version: int = 24) -> Path:
    db = root / "Default" / "Network" / "Cookies"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('version', ?)", (str(version),))
    conn.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB, path TEXT, expires_utc INTEGER, is_secure INTEGER)")
    future = int((time.time() + 3600 + EPOCH) * 1_000_000)
    for r in rows:
        conn.execute("INSERT INTO cookies VALUES (?,?,?,?,?,?,?)", (
            r["host"], r["name"], "", encrypt(r["value"], r["host"], version), r.get("path", "/"),
            r.get("expires", future), r.get("secure", 0)))
    conn.commit()
    conn.close()
    return db


@pytest.fixture(autouse=True)
def no_cached_keys():
    bc._keys.clear()


def fake_password(service, account):
    assert service == "Brave Safe Storage"
    return PASSWORD


def test_reads_and_decrypts_for_exact_host(tmp_path):
    make_db(tmp_path, [{"host": "localhost", "name": "id_token", "value": "abc.def"},
                       {"host": "other.test", "name": "x", "value": "nope"}])
    found = bc.cookies_for("http://localhost:8000/api/payees", password_fn=fake_password, root=tmp_path)
    assert found.header == "id_token=abc.def"
    assert found.browser == "Brave" and found.profile == "Default"


def test_parent_domain_cookie_applies_to_subdomain(tmp_path):
    make_db(tmp_path, [{"host": ".example.com", "name": "id_token", "value": "prod", "secure": 1},
                       {"host": "app.example.com", "name": "ui", "value": "only-app"}])
    found = bc.cookies_for("https://api.example.com/api/payees", password_fn=fake_password, root=tmp_path)
    assert found.names == ["id_token"]


def test_skips_expired_and_insecure(tmp_path):
    past = int((time.time() - 10 + EPOCH) * 1_000_000)
    make_db(tmp_path, [{"host": "api.example.test", "name": "old", "value": "1", "expires": past},
                       {"host": "api.example.test", "name": "sec", "value": "2", "secure": 1}])
    with pytest.raises(bc.BrowserCookieError, match="not signed in"):
        bc.cookies_for("http://api.example.test/", password_fn=fake_password, root=tmp_path)


def test_older_db_without_domain_hash(tmp_path):
    make_db(tmp_path, [{"host": "localhost", "name": "id_token", "value": "v"}], version=20)
    assert bc.cookies_for("http://localhost/", password_fn=fake_password, root=tmp_path).header == "id_token=v"


def test_most_specific_path_wins(tmp_path):
    make_db(tmp_path, [{"host": "localhost", "name": "s", "value": "root", "path": "/"},
                       {"host": "localhost", "name": "s", "value": "api", "path": "/api"},
                       {"host": "localhost", "name": "t", "value": "elsewhere", "path": "/admin"}])
    assert bc.cookies_for("http://localhost/api/x", password_fn=fake_password, root=tmp_path).header == "s=api"


def test_missing_browser(tmp_path):
    with pytest.raises(bc.BrowserCookieError, match="Couldn't find Brave"):
        bc.cookies_for("http://localhost/", password_fn=fake_password, root=tmp_path)
