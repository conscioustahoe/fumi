"""Files Fumi keeps in ~/.fumi. Nothing is ever written next to the spec or into its repo."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def home() -> Path:
    root = Path(os.environ.get("FUMI_HOME", Path.home() / ".fumi"))
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def write_json(path: Path, data: Any) -> None:
    """Atomic and private (mode 600) so a crash never leaves half a file."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name) or "_"


def workspace_key(spec: Path) -> str:
    """Folder name plus a short hash of the spec's full path so two specs never share state."""
    digest = hashlib.sha1(str(spec).encode()).hexdigest()[:8]
    return f"{safe_name(spec.parent.name)}-{digest}"


def workspace_dir(key: str) -> Path:
    return home() / "workspaces" / key


# ---- recent specs ----

def recent() -> list[dict]:
    return read_json(home() / "recent.json", {"recent": []})["recent"]


def clear_recent() -> None:
    (home() / "recent.json").unlink(missing_ok=True)


def remember(entry: dict) -> None:
    rest = [r for r in recent() if r["path"] != entry["path"]]
    write_json(home() / "recent.json", {"recent": [entry, *rest][:12]})


# ---- UI state per branch ----

def branch_state(key: str, branch: str) -> dict:
    return read_json(workspace_dir(key) / "branches" / f"{safe_name(branch)}.json", {})


def save_branch_state(key: str, branch: str, data: dict) -> None:
    write_json(workspace_dir(key) / "branches" / f"{safe_name(branch)}.json", data)


# ---- environments and secrets ----

def environments(key: str) -> dict | None:
    return read_json(workspace_dir(key) / "environments.json", None)


def save_environments(key: str, data: dict) -> None:
    write_json(workspace_dir(key) / "environments.json", data)


def _secrets_file(key: str, env: str) -> Path:
    return home() / "secrets" / key / f"{safe_name(env)}.json"


def secrets(key: str, env: str) -> dict:
    return read_json(_secrets_file(key, env), {})


def save_secret(key: str, env: str, name: str, value: str | None) -> None:
    data = secrets(key, env)
    if value:
        data[name] = value
    else:
        data.pop(name, None)
    write_json(_secrets_file(key, env), data)


def delete_secrets(key: str, env: str) -> None:
    _secrets_file(key, env).unlink(missing_ok=True)
