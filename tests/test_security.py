from fastapi.testclient import TestClient

from fumi.server import create_app

from conftest import BASE, H


def test_api_needs_the_fumi_header():
    c = TestClient(create_app(), base_url=BASE)
    assert c.get("/api/session").status_code == 403
    assert c.get("/api/session", headers=H).status_code == 200


def test_rejects_other_origins():
    c = TestClient(create_app(), base_url=BASE)
    assert c.get("/api/session", headers={**H, "Origin": "https://evil.example"}).status_code == 403
    assert c.get("/api/session", headers={**H, "Origin": BASE}).status_code == 200
    # A form post from another site carries its Origin and no custom header.
    assert c.post("/api/reload", headers={"Origin": "https://evil.example"}).status_code == 403


def test_rejects_other_hosts():
    c = TestClient(create_app(), base_url="http://evil.example:3737")
    assert c.get("/api/session", headers=H).status_code == 403


def test_page_loads_without_anything():
    c = TestClient(create_app(), base_url=BASE)
    assert c.get("/").status_code == 200
