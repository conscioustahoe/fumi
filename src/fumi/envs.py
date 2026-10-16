"""Environments: a base URL and a way to sign in. Each one is its own namespace and nothing cascades."""

from fumi import store

DEFAULT = {"name": "local", "base_url": "http://localhost:8000", "protected": False, "auth": {"type": "none"}}
READS = ("GET", "HEAD", "OPTIONS")


class EnvError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def load(key: str) -> dict:
    return store.environments(key) or {"active": DEFAULT["name"], "envs": [dict(DEFAULT)]}


def get(key: str, name: str | None = None) -> dict:
    data = load(key)
    name = name or data["active"]
    for env in data["envs"]:
        if env["name"] == name:
            return env
    raise EnvError(f"no environment named {name!r}", 404)


def public(key: str) -> list[dict]:
    """Environments as the UI sees them. Secret names only and never their values."""
    return [{**env, "secrets": sorted(store.secrets(key, env["name"]))} for env in load(key)["envs"]]


def set_active(key: str, name: str) -> None:
    get(key, name)
    data = load(key)
    data["active"] = name
    store.save_environments(key, data)


def put(key: str, name: str, base_url: str, protected: bool, auth: dict) -> None:
    name = name.strip()
    if not name or not all(c.isalnum() or c in "-_" for c in name):
        raise EnvError("environment names use letters digits - and _")
    url = base_url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise EnvError("base URL must start with http:// or https://")
    data = load(key)
    env = {"name": name, "base_url": url, "protected": protected, "auth": auth}
    data["envs"] = [e for e in data["envs"] if e["name"] != name] + [env]
    data["envs"].sort(key=lambda e: (e["protected"], e["name"] != "local", e["name"]))
    store.save_environments(key, data)


def delete(key: str, name: str) -> None:
    get(key, name)
    data = load(key)
    if len(data["envs"]) == 1:
        raise EnvError("keep at least one environment")
    data["envs"] = [e for e in data["envs"] if e["name"] != name]
    if data["active"] == name:
        data["active"] = data["envs"][0]["name"]
    store.save_environments(key, data)
    store.delete_secrets(key, name)


def check_write(env: dict, method: str, confirm: str | None) -> None:
    """Protected environments refuse writes until the user types the environment's name."""
    if env["protected"] and method not in READS and confirm != env["name"]:
        raise EnvError(f"{env['name']} is protected. Type its name to send a {method}", 428)
