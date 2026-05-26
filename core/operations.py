"""Unified CRUD operations for Component and Config instances.

Centralizes exception mapping so all three surfaces (API, CLI, MCP) receive a
consistent OperationResult instead of divergent try/except blocks.

ValidationError (pydantic) is intentionally NOT caught here so the API's global
handler keeps its rich field-level error format.
"""

from dataclasses import dataclass
from typing import Any, Literal

from core.errors import ETagMismatch, PreconditionRequired
from core.instances import (
    InstanceAlreadyExists,
    InstanceNotFound,
    SharedSpecConflict,
    SingletonNotInstanceable,
    create_instance,
    delete_config_instance,
    delete_instance,
    patch_config_instance,
    patch_instance,
    replace_instance,
    set_config_instance,
    set_singleton_config,
)

OpStatus = Literal["ok", "conflict", "not_found", "precondition", "etag_mismatch"]


@dataclass
class OperationResult:
    status: OpStatus
    payload: Any = None
    etag: str | None = None
    error_message: str | None = None


def _wrap_write(fn, *args, **kwargs) -> OperationResult:  # type: ignore[type-arg]
    """Call fn(*args, **kwargs) and map domain exceptions to OperationResult.

    Catches InstanceNotFound, InstanceAlreadyExists, SingletonNotInstanceable,
    SharedSpecConflict, ETagMismatch, and PreconditionRequired uniformly.
    ValidationError is left uncaught so callers can handle it surface-specifically.
    """
    try:
        result = fn(*args, **kwargs)
    except (InstanceAlreadyExists, SingletonNotInstanceable, SharedSpecConflict) as e:
        return OperationResult(status="conflict", error_message=str(e))
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_message=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_message=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition", error_message=str(e))

    if result is None:
        return OperationResult(status="ok")
    payload, etag = result
    return OperationResult(status="ok", payload=payload, etag=etag)


# ── Component CRUD ──────────────────────────────────────────────────


def create_component_op(
    system: str, component: str, instance: str, payload: dict[str, Any]
) -> OperationResult:
    return _wrap_write(create_instance, system, component, instance, payload)


def replace_component_op(
    system: str,
    component: str,
    instance: str,
    payload: dict[str, Any],
    *,
    if_match: str | None,
) -> OperationResult:
    return _wrap_write(
        replace_instance, system, component, instance, payload, expected_etag=if_match
    )


def patch_component_op(
    system: str,
    component: str,
    instance: str,
    delta: dict[str, Any],
    *,
    if_match: str | None,
) -> OperationResult:
    return _wrap_write(patch_instance, system, component, instance, delta, expected_etag=if_match)


def delete_component_op(
    system: str,
    component: str,
    instance: str,
    *,
    if_match: str | None,
) -> OperationResult:
    return _wrap_write(delete_instance, system, component, instance, expected_etag=if_match)


# ── Config CRUD ─────────────────────────────────────────────────────


def set_singleton_config_op(
    system: str,
    config: str,
    payload: dict[str, Any],
    *,
    if_match: str | None,
) -> OperationResult:
    return _wrap_write(set_singleton_config, system, config, payload, expected_etag=if_match)


def set_config_entry_op(
    system: str,
    config: str,
    key: str,
    payload: dict[str, Any],
    *,
    if_match: str | None,
) -> OperationResult:
    return _wrap_write(set_config_instance, system, config, key, payload, expected_etag=if_match)


def patch_config_entry_op(
    system: str,
    config: str,
    key: str,
    delta: dict[str, Any],
    *,
    if_match: str | None,
) -> OperationResult:
    return _wrap_write(patch_config_instance, system, config, key, delta, expected_etag=if_match)


def delete_config_entry_op(
    system: str,
    config: str,
    key: str,
    *,
    if_match: str | None,
) -> OperationResult:
    return _wrap_write(delete_config_instance, system, config, key, expected_etag=if_match)
