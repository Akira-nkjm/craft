"""Schema-only payload validation endpoints."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Body

from craft.api.errors import NotFoundError
from craft.core.instances import InstanceNotFound
from craft.core.surface_ops.validation import (
    validate_component_payload,
    validate_config_payload,
)

router = APIRouter(prefix="/validate", tags=["validate"])


@router.post("/components/{system}/{component}")
def validate_component(
    system: str,
    component: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        result = validate_component_payload(system, component, payload)
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    return asdict(result)


@router.post("/configs/{system}/{name}")
def validate_config(
    system: str,
    name: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        result = validate_config_payload(system, name, payload)
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    return asdict(result)
