"""FastAPI 経由のスモーク。"""

from fastapi.testclient import TestClient

from craft.api.main import app


def test_healthz():
    with TestClient(app) as client:
        r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_schema_endpoint():
    with TestClient(app) as client:
        r = client.get("/schema/power/battery")
    assert r.status_code == 200
    body = r.json()
    assert "properties" in body
    assert set(body["properties"]) >= {"spec", "design", "requirements", "meta"}


def test_schema_404_unknown():
    with TestClient(app) as client:
        r = client.get("/schema/power/unknown")
    assert r.status_code == 404


def test_components_list_instances():
    with TestClient(app) as client:
        r = client.get("/components/power/battery")
    assert r.status_code == 200
    body = r.json()
    assert body["plural"] == "batteries"
    assert set(body["instances"]) == {"main", "aux"}


def test_verify_endpoint():
    with TestClient(app) as client:
        r = client.post("/verify")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    power = body["scopes"]["power"]
    verif_values = {item["path"].split("?")[-1]: item["value"] for item in power["verifications"]}
    assert "verify_battery_capacity" in verif_values
