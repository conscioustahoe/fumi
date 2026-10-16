from conftest import H


def test_default_local_env(client):
    ws = client.get("/api/session", headers=H).json()["workspace"]
    assert ws["env"] == "local"
    assert [e["name"] for e in ws["envs"]] == ["local"]
    assert ws["base_url"] == "http://localhost:8000"


def test_protected_env_needs_confirmation_for_writes(client):
    r = client.put("/api/envs/prod", headers=H, json={"base_url": "http://127.0.0.1:9", "protected": True})
    assert r.status_code == 200
    req = {"env": "prod", "method": "POST", "path": "/things", "body": "{}"}
    assert client.post("/api/send", headers=H, json=req).status_code == 428
    assert client.post("/api/send", headers=H, json={**req, "confirm": "wrong"}).status_code == 428
    sent = client.post("/api/send", headers=H, json={**req, "confirm": "prod"}).json()
    assert "Can't reach" in sent["error"]  # got past the guard. Nothing listens on port 9
    reads = client.post("/api/send", headers=H, json={**req, "method": "GET"}).json()
    assert "Can't reach" in reads["error"]


def test_bad_env_input_is_rejected(client):
    assert client.put("/api/envs/no spaces", headers=H, json={"base_url": "http://x"}).status_code == 400
    assert client.put("/api/envs/dev", headers=H, json={"base_url": "ftp://x"}).status_code == 400
    assert client.delete("/api/envs/local", headers=H).status_code == 400  # the last one stays
    assert client.delete("/api/envs/nope", headers=H).status_code == 404


def test_secret_values_never_returned(client):
    client.put("/api/envs/local", headers=H, json={"base_url": "http://127.0.0.1:9", "auth": {"type": "api_key"}})
    ws = client.put("/api/envs/local/secrets/api_key", headers=H, json={"value": "sk-very-secret"}).json()
    assert ws["envs"][0]["secrets"] == ["api_key"]
    assert "sk-very-secret" not in client.get("/api/session", headers=H).text


def test_missing_api_key_explains(client):
    client.put("/api/envs/local", headers=H, json={"base_url": "http://127.0.0.1:9", "auth": {"type": "api_key"}})
    out = client.post("/api/send", headers=H, json={"env": "local", "method": "GET", "path": "/"}).json()
    assert out["auth_error"] and "No API key" in out["error"]
