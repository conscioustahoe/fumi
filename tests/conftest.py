import json
import subprocess

import pytest
from fastapi.testclient import TestClient

from fumi.server import create_app

H = {"X-Fumi": "1"}
BASE = "http://127.0.0.1:3737"

SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "things", "version": "1"},
    "paths": {"/things": {"post": {"operationId": "make_thing", "summary": "Make thing", "tags": ["things"]}}},
}


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture(autouse=True)
def fumi_home(tmp_path, monkeypatch):
    monkeypatch.setenv("FUMI_HOME", str(tmp_path / "home"))


@pytest.fixture
def repo(tmp_path):
    """A git repo with openapi.json committed on main."""
    path = tmp_path / "svc"
    path.mkdir()
    (path / "openapi.json").write_text(json.dumps(SPEC))
    git(path, "init", "-q", "-b", "main")
    git(path, "add", "-A")
    git(path, "-c", "user.name=t", "-c", "user.email=t@t.invalid", "commit", "-qm", "spec")
    return path


@pytest.fixture
def client(repo):
    with TestClient(create_app(), base_url=BASE) as c:
        r = c.post("/api/open", headers=H, json={"path": str(repo / "openapi.json")})
        assert r.status_code == 200, r.text
        yield c
