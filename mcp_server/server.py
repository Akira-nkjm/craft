"""Craft MCP サーバ — stdio 経由で Claude Code / Desktop から接続。

起動:
    uv run craft-mcp
または直接:
    uv run python -m mcp_server.server
"""

import asyncio
import json
from typing import Any

import mcp.types as mcp_types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from core.discovery import discover_subsystems
from mcp_server.tool_factory import build_handler_map, build_tool_specs


def build_server() -> Server:
    """全 subsystem を import → registry 確定 → MCP server 構築。"""
    discover_subsystems()

    server: Server = Server("craft")
    tools = build_tool_specs()
    handlers = build_handler_map()

    @server.list_tools()
    async def _list_tools() -> list[mcp_types.Tool]:
        return tools

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[mcp_types.TextContent]:
        handler = handlers.get(name)
        if handler is None:
            payload = {"error": f"unknown tool: {name}"}
        else:
            try:
                payload = handler(arguments or {})
            except Exception as e:  # noqa: BLE001
                payload = {"error": f"{type(e).__name__}: {e}"}
        return [
            mcp_types.TextContent(
                type="text",
                text=json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            )
        ]

    return server


async def _run() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """`craft-mcp` console script entry point。"""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
