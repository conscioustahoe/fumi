import json

from conftest import H, SPEC, git


def test_open_reads_the_spec(client, repo):
    ws = client.get("/api/session", headers=H).json()["workspace"]
    assert ws["name"] == "svc" and ws["branch"] == "main" and ws["spec_rel"] == "openapi.json"
    assert [o["id"] for o in ws["ops"]] == ["make_thing"]


def test_open_rejects_missing_file(client, tmp_path):
    assert client.post("/api/open", headers=H, json={"path": str(tmp_path / "nope.json")}).status_code == 400


def test_broken_spec_keeps_last_good(client, repo):
    (repo / "openapi.json").write_text("{")
    ws = client.post("/api/reload", headers=H).json()
    assert "not valid JSON" in ws["error"]
    assert [o["id"] for o in ws["ops"]] == ["make_thing"]
    assert ws["good"]["branch"] == "main"


def test_follows_branch_on_reload(client, repo):
    git(repo, "checkout", "-q", "-b", "feature")
    spec = {**SPEC, "paths": {**SPEC["paths"], "/other": {"get": {"operationId": "other"}}}}
    (repo / "openapi.json").write_text(json.dumps(spec))
    ws = client.post("/api/reload", headers=H).json()
    assert ws["branch"] == "feature"
    assert sorted(o["id"] for o in ws["ops"]) == ["make_thing", "other"]


def test_spec_outside_git(tmp_path):
    from fastapi.testclient import TestClient

    from fumi.server import create_app
    from conftest import BASE

    f = tmp_path / "plain" / "api.json"
    f.parent.mkdir()
    f.write_text(json.dumps(SPEC))
    with TestClient(create_app(), base_url=BASE) as c:
        ws = c.post("/api/open", headers=H, json={"path": str(f)}).json()
    assert ws["git"] is False and ws["branch"] == "-" and ws["name"] == "plain"


def test_branch_state_round_trip(client):
    assert client.put("/api/branch-state?branch=main", headers=H, json={"opId": "make_thing"}).status_code == 200
    assert client.get("/api/branch-state?branch=main", headers=H).json() == {"opId": "make_thing"}


def test_recent_and_clear(client, repo):
    recent = client.get("/api/session", headers=H).json()["recent"]
    assert [r["path"] for r in recent] == [str(repo / "openapi.json")]
    assert client.delete("/api/recent", headers=H).json() == {"recent": []}
    assert client.get("/api/session", headers=H).json()["recent"] == []
