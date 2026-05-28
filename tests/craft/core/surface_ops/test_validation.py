"""Unit tests for schema-only payload validation surface ops."""

import pytest

from craft.core.discovery import discover_systems
from craft.core.instances import InstanceNotFound
from craft.core.surface_ops.validation import validate_component_payload


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


def test_validate_component_payload_accepts_valid_payload():
    discover_systems()

    result = validate_component_payload("power", "battery", _valid_battery_payload())

    assert result.ok is True
    assert result.errors == []


def test_validate_component_payload_returns_errors_for_invalid_payload():
    discover_systems()
    payload = _valid_battery_payload()
    payload["spec"]["capacity_wh"] = -1.0

    result = validate_component_payload("power", "battery", payload)

    assert result.ok is False
    assert any("capacity_wh" in str(error["loc"]) for error in result.errors)


def test_validate_component_payload_raises_for_unknown_component():
    discover_systems()

    with pytest.raises(InstanceNotFound, match="Component 'power.unknown' is not registered"):
        validate_component_payload("power", "unknown", {})
