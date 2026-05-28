"""MCP validation tool integration tests."""

import json
from typing import Any

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from craft.mcp_server.server import build_server


def _decode(call_result: Any) -> Any:
    content = call_result.content[0]
    assert isinstance(content, TextContent), f"expected TextContent, got {type(content)}"
    return json.loads(content.text)


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


@pytest.mark.asyncio
async def test_validate_tools_are_listed():
    async with create_connected_server_and_client_session(build_server()) as client:
        result = await client.list_tools()

    names = {tool.name for tool in result.tools}
    assert {"validate_component", "validate_config"} <= names


@pytest.mark.asyncio
async def test_validate_component_tool_accepts_valid_payload():
    async with create_connected_server_and_client_session(build_server()) as client:
        result = await client.call_tool(
            "validate_component",
            {
                "system": "power",
                "component": "battery",
                "payload": _valid_battery_payload(),
            },
        )

    assert _decode(result) == {"ok": True, "errors": []}


@pytest.mark.asyncio
async def test_validate_component_tool_returns_validation_errors():
    payload = _valid_battery_payload()
    payload["spec"]["capacity_wh"] = -1.0

    async with create_connected_server_and_client_session(build_server()) as client:
        result = await client.call_tool(
            "validate_component",
            {"system": "power", "component": "battery", "payload": payload},
        )

    body = _decode(result)
    assert body["ok"] is False
    assert any("capacity_wh" in str(error["loc"]) for error in body["errors"])


@pytest.mark.asyncio
async def test_validate_config_tool_accepts_valid_payload():
    async with create_connected_server_and_client_session(build_server()) as client:
        result = await client.call_tool(
            "validate_config",
            {
                "system": "mission",
                "name": "missionprofile",
                "payload": _valid_mission_profile_payload(),
            },
        )

    assert _decode(result) == {"ok": True, "errors": []}
