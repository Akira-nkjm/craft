"""Verification run persistence API tests."""

from fastapi.testclient import TestClient

from craft.api.main import app


def test_verify_creates_run_artifact(clean_generated_dir):
    with TestClient(app) as client:
        response = client.post("/verify")
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert (clean_generated_dir / "runs" / run_id / "result.toml").exists()


def test_runs_list(clean_generated_dir):
    with TestClient(app) as client:
        first = client.post("/verify")
        second = client.post("/verify")
        response = client.get("/runs")
    assert first.status_code == 200
    assert second.status_code == 200
    assert response.status_code == 200
    assert len(response.json()["runs"]) >= 2


def test_runs_latest_after_verify(clean_generated_dir):
    with TestClient(app) as client:
        verify_response = client.post("/verify")
        latest_response = client.get("/runs/latest")
    assert verify_response.status_code == 200
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == verify_response.json()["run_id"]


def test_run_not_found(clean_generated_dir):
    with TestClient(app) as client:
        response = client.get("/runs/nonexistent")
    assert response.status_code == 404
    assert response.json()["type"] == "not_found"


def test_artifact_meta_json(clean_generated_dir):
    with TestClient(app) as client:
        verify_response = client.post("/verify")
        run_id = verify_response.json()["run_id"]
        artifact_response = client.get(f"/runs/{run_id}/artifacts/meta.json")
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("application/json")
    assert "status" in artifact_response.json()
