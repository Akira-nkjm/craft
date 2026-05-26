"""MCP server のスモークテスト。

`create_connected_server_and_client_session` で memory transport を張り、
client → server の roundtrip を確認する。
"""

import json
from typing import Any

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server.server import build_server


@pytest.fixture
def mcp_server():
    return build_server()


def _decode(call_result: Any) -> Any:
    """CallToolResult.content[0] が TextContent である前提で JSON parse。"""
    content = call_result.content[0]
    assert isinstance(content, TextContent), f"expected TextContent, got {type(content)}"
    return json.loads(content.text)


@pytest.mark.asyncio
async def test_list_tools_exposes_registry(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.list_tools()
    names = {t.name for t in result.tools}
    # introspection
    assert {"list_subsystems", "list_components", "list_configs", "list_analyses"} <= names
    # multi-instance
    assert {"list_batteries", "get_battery", "list_pdms", "list_heaters"} <= names
    # singleton
    assert "get_obc" in names
    # config
    assert {"get_missionprofile", "get_orbitalparameters"} <= names
    # analysis
    assert "analyze_battery_eol_capacity" in names
    # verify
    assert "verify_all" in names
    assert "verify_verify_battery_capacity" in names


@pytest.mark.asyncio
async def test_list_subsystems_tool(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("list_subsystems", {})
    body = _decode(result)
    assert set(body) == {"power", "cdh", "thermal", "mission", "orbital"}


@pytest.mark.asyncio
async def test_get_battery_with_name(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("get_battery", {"name": "main"})
    body = _decode(result)
    assert "etag" in body
    assert body["spec"]["capacity_wh"] == 100.0


@pytest.mark.asyncio
async def test_get_obc_singleton(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("get_obc", {})
    body = _decode(result)
    assert body["spec"]["clock_mhz"] == 100


@pytest.mark.asyncio
async def test_get_mission_config(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("get_missionprofile", {})
    body = _decode(result)
    assert body["duration_years"] == 5.0


@pytest.mark.asyncio
async def test_analyze_adhoc(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool(
            "analyze_battery_eol_capacity",
            {"initial_capacity_wh": 100.0, "years": 5.0, "cycles_per_day": 2.0},
        )
    body = _decode(result)
    assert body["value"] == 80.0


@pytest.mark.asyncio
async def test_verify_all(mcp_server, clean_generated_dir):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("verify_all", {})
    body = _decode(result)
    assert body["success"] is True
    assert "power" in body["scopes"]


@pytest.mark.asyncio
async def test_get_schema_tool(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool(
            "get_schema",
            {"subsystem": "power", "component": "battery"},
        )
    body = _decode(result)
    assert "properties" in body
    assert set(body["properties"]) >= {"spec", "design", "requirements"}


@pytest.mark.asyncio
async def test_unknown_tool_returns_error(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("does_not_exist", {})
    body = _decode(result)
    assert "error" in body
