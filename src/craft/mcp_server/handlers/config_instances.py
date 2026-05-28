"""Multi-instance config MCP tool handlers."""

from typing import Any

from pydantic import ValidationError

from craft.core.errors import PreconditionRequired
from craft.core.instances import InstanceNotFound, get_config_instance
from craft.core.surface_ops.concurrency import ETagMode, resolve_expected_etag
from craft.core.surface_ops.operations import (
    delete_config_entry_op,
    patch_config_entry_op,
    set_config_entry_op,
)
from craft.mcp_server.error_mapping import error_or_none


def handle_get_config_instance(system: str, name: str, key: str) -> Any:
    try:
        data, etag = get_config_instance(system, name, key)
    except InstanceNotFound as e:
        return {"error": str(e)}
    return {"etag": etag, **data}


def handle_set_config_instance(system: str, name: str, payload: dict[str, Any]) -> Any:
    key = payload.get("key", "")
    if not key:
        return {"error": "key required"}
    data_payload = payload.get("data")
    if not isinstance(data_payload, dict):
        return {"error": "data (object) required"}
    try:
        result = set_config_entry_op(system, name, key, data_payload, if_match=payload.get("etag"))
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}


def handle_patch_config_instance(system: str, name: str, payload: dict[str, Any]) -> Any:
    key = payload.get("key", "")
    if not key:
        return {"error": "key required"}
    delta = payload.get("delta") or {}
    if not isinstance(delta, dict):
        return {"error": "delta must be an object"}
    etag = payload.get("etag")
    auto_etag = bool(payload.get("auto_etag", False))
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: get_config_instance(system, name, key)[1]
        )
    except PreconditionRequired as e:
        return {"error": str(e)}
    except InstanceNotFound as e:
        return {"error": str(e)}
    try:
        result = patch_config_entry_op(system, name, key, delta, if_match=resolved_etag)
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}


def handle_delete_config_instance(system: str, name: str, payload: dict[str, Any]) -> Any:
    key = payload.get("key", "")
    if not key:
        return {"error": "key required"}
    etag = payload.get("etag")
    auto_etag = bool(payload.get("auto_etag", False))
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: get_config_instance(system, name, key)[1]
        )
    except PreconditionRequired as e:
        return {"error": str(e)}
    except InstanceNotFound as e:
        return {"error": str(e)}
    result = delete_config_entry_op(system, name, key, if_match=resolved_etag)
    if err := error_or_none(result):
        return err
    return {"deleted": True, "key": key}
