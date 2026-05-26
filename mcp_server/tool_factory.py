"""Registry → MCP tool 定義の自動生成。

仕様: plan/Craft/01_仕様/MCP設計.md §2-3
"""

from collections.abc import Callable
from typing import Any

import mcp.types as mcp_types

from mcp_server.tools import analyses, components, configs, history, introspection, verify


def build_tool_specs() -> list[mcp_types.Tool]:
    """registry を走査して MCP tool 定義を生成。"""
    return [
        *introspection.specs(),
        *components.specs(),
        *configs.specs(),
        *analyses.specs(),
        *verify.specs(),
        *history.specs(),
    ]


def build_handler_map() -> dict[str, Callable[[dict[str, Any]], Any]]:
    """tool name → handler 関数の dict を返す。"""
    handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
    handlers.update(introspection.handlers())
    handlers.update(components.handlers())
    handlers.update(configs.handlers())
    handlers.update(analyses.handlers())
    handlers.update(verify.handlers())
    handlers.update(history.handlers())
    return handlers
