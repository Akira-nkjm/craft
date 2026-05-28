"""Introspection MCP tool handlers."""

from typing import Any

from craft.schema import default_registry


def handle_list_introspection(kind: str) -> Any:
    """list_systems / list_components / list_configs / list_analyses。"""
    if kind == "systems":
        return sorted(default_registry.systems())
    if kind == "components":
        return [
            {
                "system": c.system,
                "name": c.name,
                "plural": c.plural,
                "cardinality": c.cardinality,
                "traits": list(c.traits),
            }
            for c in default_registry.components()
        ]
    if kind == "configs":
        return [
            {"system": c.system, "name": c.name, "plural": c.plural, "cardinality": c.cardinality}
            for c in default_registry.configs()
        ]
    if kind == "analyses":
        return [
            {
                "system": a.system,
                "name": a.name,
                "verify": a.verify,
                "desc": a.desc,
            }
            for a in default_registry.analyses()
        ]
    raise ValueError(f"Unknown introspection kind: {kind}")


def handle_get_schema(payload: dict[str, Any]) -> Any:
    system = payload.get("system", "")
    component = payload.get("component", "")
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        return {"error": f"component '{system}.{component}' not found"}
    return defn.entry.model_json_schema()
