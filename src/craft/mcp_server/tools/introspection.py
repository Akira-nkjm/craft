"""introspection ツール (list_* / get_schema) の spec と handler。"""

from collections.abc import Callable
from typing import Any

import mcp.types as mcp_types

from craft.mcp_server.handlers import handle_get_schema, handle_list_introspection


def specs() -> list[mcp_types.Tool]:
    empty: dict[str, Any] = {"type": "object", "properties": {}}
    return [
        mcp_types.Tool(
            name="list_systems",
            description="登録済み system の一覧を返す。",
            inputSchema=empty,
        ),
        mcp_types.Tool(
            name="list_components",
            description="全 component の (system, name, plural, cardinality, traits) を返す。",
            inputSchema=empty,
        ),
        mcp_types.Tool(
            name="list_configs",
            description="全 config の (system, name) を返す。",
            inputSchema=empty,
        ),
        mcp_types.Tool(
            name="list_analyses",
            description="全 @analysis の (system, name, verify, desc) を返す。",
            inputSchema=empty,
        ),
        mcp_types.Tool(
            name="get_schema",
            description="component の JSON Schema (Entry model) を返す。",
            inputSchema={
                "type": "object",
                "properties": {
                    "system": {"type": "string"},
                    "component": {"type": "string"},
                },
                "required": ["system", "component"],
            },
        ),
    ]


def handlers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    return {
        "list_systems": lambda _: handle_list_introspection("systems"),
        "list_components": lambda _: handle_list_introspection("components"),
        "list_configs": lambda _: handle_list_introspection("configs"),
        "list_analyses": lambda _: handle_list_introspection("analyses"),
        "get_schema": handle_get_schema,
    }
