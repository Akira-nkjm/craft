"""Ad-hoc analysis cache tests."""

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from api.main import app as api_app
from cli.main import app as cli_app


def test_cache_hit_returns_same_value(clean_generated_dir):
    payload = {"initial_capacity_wh": 100.0, "years": 5.0, "cycles_per_day": 1.0}
    with TestClient(api_app) as client:
        first = client.post("/analyses/_/battery_eol_capacity", json=payload)
        second = client.post("/analyses/_/battery_eol_capacity", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["value"] == second.json()["value"]
    assert first.json()["cache_hit"] is False
    assert second.json()["cache_hit"] is True


def test_cache_miss_for_different_inputs(clean_generated_dir):
    with TestClient(api_app) as client:
        first = client.post(
            "/analyses/_/battery_eol_capacity",
            json={"initial_capacity_wh": 100.0, "years": 5.0, "cycles_per_day": 1.0},
        )
        second = client.post(
            "/analyses/_/battery_eol_capacity",
            json={"initial_capacity_wh": 100.0, "years": 6.0, "cycles_per_day": 1.0},
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["cache_hit"] is False
    assert second.json()["cache_hit"] is False


def test_no_cache_flag_bypasses(clean_generated_dir):
    runner = CliRunner()
    payload = json.dumps({"initial_capacity_wh": 100.0, "years": 5.0, "cycles_per_day": 1.0})
    first = runner.invoke(
        cli_app,
        ["analysis", "run", "_", "battery_eol_capacity", "--payload", payload],
    )
    second = runner.invoke(
        cli_app,
        ["analysis", "run", "_", "battery_eol_capacity", "--payload", payload, "--no-cache"],
    )
    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    assert json.loads(first.stdout)["cache_hit"] is False
    assert json.loads(second.stdout)["cache_hit"] is False
