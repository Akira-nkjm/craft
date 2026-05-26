"""Unified CRUD operation wrappers — single source of exception mapping.

Each function calls a core.instances function and returns an OperationResult,
so API / CLI / MCP surfaces share identical exception capture logic.
"""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

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

OperationStatus = Literal[
    "ok",
    "conflict",
    "not_found",
    "validation",
    "etag_mismatch",
    "precondition_required",
]


@dataclass
class OperationResult:
    status: OperationStatus
    payload: Any = None
    error_code: str | None = None
    etag: str | None = None
    exc: BaseException | None = None  # preserved for surfaces that need to re-raise


# ─── Component ops ────────────────────────────────────────────────────


def create_component_op(
    system: str, component: str, instance: str, payload: dict[str, Any]
) -> OperationResult:
    try:
        created, etag = create_instance(system, component, instance, payload)
    except (InstanceAlreadyExists, SingletonNotInstanceable, SharedSpecConflict) as e:
        return OperationResult(status="conflict", error_code=str(e))
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except ValidationError as e:
        return OperationResult(status="validation", error_code=str(e), exc=e)
    return OperationResult(status="ok", payload=created, etag=etag)


def replace_component_op(
    system: str,
    component: str,
    instance: str,
    payload: dict[str, Any],
    *,
    expected_etag: str | None,
) -> OperationResult:
    try:
        updated, etag = replace_instance(
            system, component, instance, payload, expected_etag=expected_etag
        )
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except SharedSpecConflict as e:
        return OperationResult(status="conflict", error_code=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_code=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition_required", error_code=str(e))
    except ValidationError as e:
        return OperationResult(status="validation", error_code=str(e), exc=e)
    return OperationResult(status="ok", payload=updated, etag=etag)


def patch_component_op(
    system: str,
    component: str,
    instance: str,
    delta: dict[str, Any],
    *,
    expected_etag: str | None,
) -> OperationResult:
    try:
        updated, etag = patch_instance(
            system, component, instance, delta, expected_etag=expected_etag
        )
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except SharedSpecConflict as e:
        return OperationResult(status="conflict", error_code=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_code=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition_required", error_code=str(e))
    except ValidationError as e:
        return OperationResult(status="validation", error_code=str(e), exc=e)
    return OperationResult(status="ok", payload=updated, etag=etag)


def delete_component_op(
    system: str,
    component: str,
    instance: str,
    *,
    expected_etag: str | None,
) -> OperationResult:
    try:
        delete_instance(system, component, instance, expected_etag=expected_etag)
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except (SingletonNotInstanceable, SharedSpecConflict) as e:
        return OperationResult(status="conflict", error_code=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_code=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition_required", error_code=str(e))
    return OperationResult(status="ok")


# ─── Config ops ───────────────────────────────────────────────────────


def set_singleton_config_op(
    system: str,
    config: str,
    payload: dict[str, Any],
    *,
    expected_etag: str | None,
) -> OperationResult:
    try:
        updated, etag = set_singleton_config(system, config, payload, expected_etag=expected_etag)
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except SingletonNotInstanceable as e:
        return OperationResult(status="conflict", error_code=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_code=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition_required", error_code=str(e))
    except ValidationError as e:
        return OperationResult(status="validation", error_code=str(e), exc=e)
    return OperationResult(status="ok", payload=updated, etag=etag)


def set_config_instance_op(
    system: str,
    config: str,
    key: str,
    payload: dict[str, Any],
    *,
    expected_etag: str | None,
) -> OperationResult:
    try:
        updated, etag = set_config_instance(
            system, config, key, payload, expected_etag=expected_etag
        )
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except SingletonNotInstanceable as e:
        return OperationResult(status="conflict", error_code=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_code=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition_required", error_code=str(e))
    except ValidationError as e:
        return OperationResult(status="validation", error_code=str(e), exc=e)
    return OperationResult(status="ok", payload=updated, etag=etag)


def patch_config_instance_op(
    system: str,
    config: str,
    key: str,
    delta: dict[str, Any],
    *,
    expected_etag: str | None,
) -> OperationResult:
    try:
        updated, etag = patch_config_instance(
            system, config, key, delta, expected_etag=expected_etag
        )
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_code=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition_required", error_code=str(e))
    except ValidationError as e:
        return OperationResult(status="validation", error_code=str(e), exc=e)
    return OperationResult(status="ok", payload=updated, etag=etag)


def delete_config_instance_op(
    system: str,
    config: str,
    key: str,
    *,
    expected_etag: str | None,
) -> OperationResult:
    try:
        delete_config_instance(system, config, key, expected_etag=expected_etag)
    except InstanceNotFound as e:
        return OperationResult(status="not_found", error_code=str(e))
    except SingletonNotInstanceable as e:
        return OperationResult(status="conflict", error_code=str(e))
    except ETagMismatch as e:
        return OperationResult(status="etag_mismatch", error_code=str(e))
    except PreconditionRequired as e:
        return OperationResult(status="precondition_required", error_code=str(e))
    return OperationResult(status="ok")
