"""Schema-only validation MCP tools."""

from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import mcp.types as mcp_types

from craft.core.surface_ops.validation import (
    validate_component_payload,
    validate_config_payload,
)


def specs() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="validate_component",
            description="Validate a Component payload with Pydantic only; no data is written.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system": {"type": "string"},
                    "component": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["system", "component", "payload"],
            },
        ),
        mcp_types.Tool(
            name="validate_config",
            description="Validate a Config payload with Pydantic only; no data is written.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system": {"type": "string"},
                    "name": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["system", "name", "payload"],
            },
        ),
    ]


def _validate_component(payload: dict[str, Any]) -> dict[str, Any]:
    result = validate_component_payload(
        str(payload.get("system", "")),
        str(payload.get("component", "")),
        _object_payload(payload.get("payload")),
    )
    return asdict(result)


def _validate_config(payload: dict[str, Any]) -> dict[str, Any]:
    result = validate_config_payload(
        str(payload.get("system", "")),
        str(payload.get("name", "")),
        _object_payload(payload.get("payload")),
    )
    return asdict(result)


def _object_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return value


def handlers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    return {
        "validate_component": _validate_component,
        "validate_config": _validate_config,
    }
