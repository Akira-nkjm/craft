"""Schema-only payload validation shared by CLI / API / MCP surfaces."""

from dataclasses import dataclass
from typing import Any, cast

from pydantic import ValidationError

from craft.core.instances import InstanceNotFound
from craft.schema import default_registry


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    errors: list[dict[str, Any]]


def validate_component_payload(
    system: str, component: str, payload: dict[str, Any]
) -> ValidationResult:
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        raise InstanceNotFound(f"Component '{system}.{component}' is not registered")
    try:
        defn.entry.model_validate(payload)
    except ValidationError as e:
        return ValidationResult(ok=False, errors=cast(list[dict[str, Any]], e.errors()))
    return ValidationResult(ok=True, errors=[])


def validate_config_payload(system: str, name: str, payload: dict[str, Any]) -> ValidationResult:
    defn = default_registry._configs.get((system, name))
    if defn is None:
        raise InstanceNotFound(f"Config '{system}.{name}' is not registered")
    try:
        defn.model.model_validate(payload)
    except ValidationError as e:
        return ValidationResult(ok=False, errors=cast(list[dict[str, Any]], e.errors()))
    return ValidationResult(ok=True, errors=[])
