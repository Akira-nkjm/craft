"""CLI validation command tests."""

import json

from typer.testing import CliRunner

from craft.cli.main import app


def _valid_battery_payload():
    return {
        "spec": {
            "capacity_wh": 100.0,
            "nominal_voltage_v": 3.7,
            "manufacturer": "Saft",
            "temp_min_c": -20.0,
            "temp_max_c": 60.0,
        },
        "design": {"depth_of_discharge": 0.7},
        "requirements": {"depth_of_discharge_max": 0.8},
    }


def _valid_mission_profile_payload():
    return {
        "duration_years": 5.0,
        "target_altitude_km": 550.0,
        "primary_payload": "camera",
        "contact_frequency_per_day": 4,
        "launch_window_start": "2027-01-01T00:00:00Z",
    }


def test_validate_component_cli_accepts_valid_payload():
    payload = json.dumps(_valid_battery_payload())

    result = CliRunner().invoke(
        app,
        ["validate", "component", "power", "battery", "--json", payload],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"ok": True, "errors": []}


def test_validate_component_cli_exits_one_for_invalid_payload():
    payload = _valid_battery_payload()
    payload["spec"]["capacity_wh"] = -1.0

    result = CliRunner().invoke(
        app,
        ["validate", "component", "power", "battery", "--json", json.dumps(payload)],
    )

    assert result.exit_code == 1
    body = json.loads(result.output)
    assert body["ok"] is False
    assert any("capacity_wh" in str(error["loc"]) for error in body["errors"])


def test_validate_config_cli_accepts_stdin_payload():
    result = CliRunner().invoke(
        app,
        ["validate", "config", "mission", "missionprofile", "--stdin"],
        input=json.dumps(_valid_mission_profile_payload()),
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"ok": True, "errors": []}
