"""Async verification job tests."""

import time

from fastapi.testclient import TestClient

from craft.api.main import app


def test_verify_async_returns_job_id(clean_generated_dir):
    with TestClient(app) as client:
        response = client.post("/verify/async")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"]
    assert body["status"] in {"queued", "running", "success"}


def test_job_completes_with_run_id(clean_generated_dir):
    with TestClient(app) as client:
        response = client.post("/verify/async")
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        job = None
        for _ in range(50):
            job_response = client.get(f"/runs/{job_id}")
            assert job_response.status_code == 200
            job = job_response.json()
            if job["status"] in {"success", "failure"}:
                break
            time.sleep(0.05)
        assert job is not None
        assert job["status"] == "success"
        run_id = job["result"]["run_id"]
        run_response = client.get(f"/runs/{run_id}")
    assert run_response.status_code == 200
