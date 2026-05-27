"""API: /merge, /merged, /scaffold, /verify (via merged.toml) のスモーク。"""

from fastapi.testclient import TestClient

from api.main import app


def test_post_merge(clean_generated_dir):
    with TestClient(app) as client:
        r = client.post("/merge")
    assert r.status_code == 200
    body = r.json()
    assert "power" in body["systems"]
    assert body["written"] is True
    assert body["stale"] is False


def test_get_merged(clean_generated_dir):
    with TestClient(app) as client:
        client.post("/merge")
        r = client.get("/merged")
    assert r.status_code == 200
    assert "[power.model" in r.text


def test_get_merged_404_if_no_merge(clean_generated_dir):
    with TestClient(app) as client:
        r = client.get("/merged")
    assert r.status_code == 404


def test_post_scaffold_dry(power_data_backup):
    with TestClient(app) as client:
        r = client.post("/scaffold?dry_run=true")
    assert r.status_code == 200
    assert any(res["system"] == "power" for res in r.json()["results"])


def test_post_scaffold_system(power_data_backup):
    with TestClient(app) as client:
        r = client.post("/scaffold/power?dry_run=true")
    assert r.status_code == 200
    assert r.json()["system"] == "power"


def test_post_scaffold_unknown_404():
    with TestClient(app) as client:
        r = client.post("/scaffold/unknown")
    assert r.status_code == 404


def test_verify_via_merged(clean_generated_dir):
    """/verify は内部で merge → merged.toml → veriq を回す。"""
    with TestClient(app) as client:
        r = client.post("/verify")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "power" in body["merge"]["systems"]
