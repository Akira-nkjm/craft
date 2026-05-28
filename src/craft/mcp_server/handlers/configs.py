"""Singleton config MCP tool handlers."""

from typing import Any

from pydantic import ValidationError

from craft.core.instances import get_singleton_config, list_config_instances
from craft.core.surface_ops.operations import set_singleton_config_op
from craft.mcp_server.error_mapping import error_or_none
from craft.schema import default_registry


def handle_get_config(system: str, name: str) -> Any:
    cfg = default_registry._configs.get((system, name))
    if cfg is None:
        return {"error": f"config '{system}.{name}' not found"}
    if cfg.cardinality == "multi":
        return list_config_instances(system, name)
    data, _ = get_singleton_config(system, name)
    return data


def handle_set_config(system: str, name: str, payload: dict[str, Any]) -> Any:
    """Singleton config 全置換。"""
    data_payload = payload.get("data")
    if not isinstance(data_payload, dict):
        return {"error": "data (object) required"}
    try:
        result = set_singleton_config_op(system, name, data_payload, if_match=payload.get("etag"))
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}
