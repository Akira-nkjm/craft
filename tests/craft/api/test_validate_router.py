"""Validation router integration tests."""

from fastapi.testclient import TestClient

from craft.api.main import app


def _client() -> TestClient:
    return TestClient(app)


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


def test_validate_component_endpoint_accepts_valid_payload():
    with _client() as client:
        response = client.post(
            "/validate/components/power/battery",
            json=_valid_battery_payload(),
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "errors": []}


def test_validate_component_endpoint_returns_validation_errors():
    payload = _valid_battery_payload()
    payload["spec"]["capacity_wh"] = -1.0

    with _client() as client:
        response = client.post("/validate/components/power/battery", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert any("capacity_wh" in str(error["loc"]) for error in body["errors"])


def test_validate_config_endpoint_accepts_valid_payload():
    with _client() as client:
        response = client.post(
            "/validate/configs/mission/missionprofile",
            json=_valid_mission_profile_payload(),
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "errors": []}


def test_validate_endpoint_returns_404_for_unknown_component():
    with _client() as client:
        response = client.post("/validate/components/power/unknown", json={})

    assert response.status_code == 404
    assert response.json()["type"] == "not_found"
