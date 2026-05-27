"""History / diff ツールの spec と handler。"""

from collections.abc import Callable
from typing import Any

import mcp.types as mcp_types

from craft.mcp_server.handlers import handle_diff, handle_history


def specs() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="history",
            description="git log entries (optionally filtered by path / limit).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        ),
        mcp_types.Tool(
            name="diff",
            description="git diff between two refs (optional path filter).",
            inputSchema={
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["from", "to"],
            },
        ),
    ]


def handlers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    return {
        "history": handle_history,
        "diff": handle_diff,
    }
