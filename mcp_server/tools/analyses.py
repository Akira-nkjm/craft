"""Analysis ツール (analyze_*) の spec と handler。"""

import inspect
from collections.abc import Callable
from functools import partial
from typing import Any

import mcp.types as mcp_types

from mcp_server.handlers import handle_analysis
from schema import default_registry


def _python_to_json_type(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "string"
    if annotation is float:
        return "number"
    if annotation is int:
        return "integer"
    if annotation is bool:
        return "boolean"
    return "string"


def _analysis_input_schema(adef: Any) -> dict[str, Any]:
    """ad-hoc analysis のみ直接 input を受け取る。veriq 経由はデータ駆動。"""
    if adef.system is not None:
        return {"type": "object", "properties": {}}
    sig = inspect.signature(adef.func)
    props: dict[str, Any] = {}
    required: list[str] = []
    for param in sig.parameters.values():
        props[param.name] = {"type": _python_to_json_type(param.annotation)}
        if param.default is inspect.Parameter.empty:
            required.append(param.name)
    return {"type": "object", "properties": props, "required": required}


def specs() -> list[mcp_types.Tool]:
    out: list[mcp_types.Tool] = []
    for adef in default_registry.analyses():
        if adef.verify:
            continue
        out.append(
            mcp_types.Tool(
                name=f"analyze_{adef.name}",
                description=adef.desc or f"Run analysis {adef.name}",
                inputSchema=_analysis_input_schema(adef),
            )
        )
    return out


def handlers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    h: dict[str, Callable[[dict[str, Any]], Any]] = {}
    for adef in default_registry.analyses():
        if not adef.verify:
            h[f"analyze_{adef.name}"] = partial(handle_analysis, adef.system, adef.name)
    return h
