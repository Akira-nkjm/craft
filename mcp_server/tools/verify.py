"""Verify ツール (verify_all / verify_*) の spec と handler。"""

from collections.abc import Callable
from functools import partial
from typing import Any

import mcp.types as mcp_types

from mcp_server.handlers import handle_verify_all, handle_verify_single
from schema import default_registry


def _verify_single(system: str, name: str, _payload: dict[str, Any]) -> Any:
    return handle_verify_single(system, name)


def specs() -> list[mcp_types.Tool]:
    tools: list[mcp_types.Tool] = [
        mcp_types.Tool(
            name="verify_all",
            description="全 system の verification を実行。",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
    for adef in default_registry.analyses(verify=True):
        if adef.system is None:
            continue
        tools.append(
            mcp_types.Tool(
                name=f"verify_{adef.name}",
                description=adef.desc or f"Run verification {adef.name}",
                inputSchema={"type": "object", "properties": {}},
            )
        )
    return tools


def handlers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    h: dict[str, Callable[[dict[str, Any]], Any]] = {
        "verify_all": lambda _: handle_verify_all(),
    }
    for adef in default_registry.analyses(verify=True):
        if adef.system is not None:
            h[f"verify_{adef.name}"] = partial(_verify_single, adef.system, adef.name)
    return h
