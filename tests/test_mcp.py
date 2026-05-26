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
    assert {"list_systems", "list_components", "list_configs", "list_analyses"} <= names
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
async def test_list_systems_tool(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("list_systems", {})
    body = _decode(result)
    assert set(body) == {"aocs", "power", "cdh", "thermal", "mission", "orbital"}


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
            {"system": "power", "component": "battery"},
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


# ─── write / history tools ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_battery_creates_instance(mcp_server, power_data_backup):
    async with create_connected_server_and_client_session(mcp_server) as client:
        add_result = await client.call_tool(
            "add_battery",
            {
                "name": "spare",
                "design": {"depth_of_discharge": 0.6},
                "requirements": {"depth_of_discharge_max": 0.8},
            },
        )
        body = _decode(add_result)
        assert "etag" in body, body
        # view には shared spec が merge される
        assert body["spec"]["capacity_wh"] == 100.0

        # 後続 get で確認
        got = await client.call_tool("get_battery", {"name": "spare"})
        got_body = _decode(got)
        assert got_body["design"]["depth_of_discharge"] == 0.6


@pytest.mark.asyncio
async def test_patch_battery(mcp_server, power_data_backup):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool(
            "patch_battery",
            {
                "name": "main",
                "delta": {"design": {"depth_of_discharge": 0.55}},
            },
        )
    body = _decode(result)
    assert "etag" in body, body
    assert body["design"]["depth_of_discharge"] == 0.55
    # shared spec が merge されているので capacity_wh は保持
    assert body["spec"]["capacity_wh"] == 100.0


@pytest.mark.asyncio
async def test_delete_battery(mcp_server, power_data_backup):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("delete_battery", {"name": "aux"})
        body = _decode(result)
        assert body.get("deleted") is True

        got = await client.call_tool("get_battery", {"name": "aux"})
        got_body = _decode(got)
        assert "error" in got_body


@pytest.mark.asyncio
async def test_set_batteries_spec(mcp_server, power_data_backup):
    async with create_connected_server_and_client_session(mcp_server) as client:
        new_spec = {
            "capacity_wh": 150.0,
            "nominal_voltage_v": 3.7,
            "manufacturer": "Saft",
            "temp_min_c": -20.0,
            "temp_max_c": 60.0,
        }
        result = await client.call_tool("set_batteries_spec", {"spec": new_spec})
        body = _decode(result)
        assert "etag" in body, body
        assert body["capacity_wh"] == 150.0

        got = await client.call_tool("get_battery", {"name": "main"})
        got_body = _decode(got)
        assert got_body["spec"]["capacity_wh"] == 150.0


@pytest.mark.asyncio
async def test_history_tool(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("history", {"limit": 3})
    body = _decode(result)
    assert "entries" in body, body
    assert len(body["entries"]) <= 3


@pytest.mark.asyncio
async def test_diff_tool_bad_sha(mcp_server):
    async with create_connected_server_and_client_session(mcp_server) as client:
        result = await client.call_tool("diff", {"from": "nonexistent_sha_xyz", "to": "HEAD"})
    body = _decode(result)
    assert "error" in body, body
