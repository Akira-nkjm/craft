"""GET /schema/{system}/{component} — Pydantic JSON Schema 配信。"""

from typing import Any

from fastapi import APIRouter

from api.errors import NotFoundError
from schema import default_registry

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/{system}/{component}")
def get_component_schema(system: str, component: str) -> dict[str, Any]:
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        raise NotFoundError(f"Component '{system}.{component}' not found in registry")
    return defn.entry.model_json_schema()


@router.get("")
def list_components() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for c in default_registry.components():
        out.setdefault(c.system, []).append(
            {
                "name": c.name,
                "plural": c.plural,
                "cardinality": c.cardinality,
                "traits": list(c.traits),
            }
        )
    return out
