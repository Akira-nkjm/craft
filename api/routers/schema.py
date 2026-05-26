"""GET /schema/{subsystem}/{component} — Pydantic JSON Schema 配信。"""

from typing import Any

from fastapi import APIRouter

from api.errors import NotFoundError
from schema import default_registry

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/{subsystem}/{component}")
def get_component_schema(subsystem: str, component: str) -> dict[str, Any]:
    defn = default_registry.component_or_none(subsystem, component)
    if defn is None:
        raise NotFoundError(f"Component '{subsystem}.{component}' not found in registry")
    return defn.entry.model_json_schema()


@router.get("")
def list_components() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for c in default_registry.components():
        out.setdefault(c.subsystem, []).append(
            {
                "name": c.name,
                "plural": c.plural,
                "cardinality": c.cardinality,
                "traits": list(c.traits),
            }
        )
    return out
