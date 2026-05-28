"""Analysis MCP tool handlers."""

from typing import Any

from craft.core.serialization import to_jsonable
from craft.mcp_server.handlers.verify import _run_veriq_node
from craft.schema import default_registry


def handle_analysis(system: str | None, name: str, payload: dict[str, Any]) -> Any:
    """ad-hoc 関数を直接呼ぶ / veriq 経由なら evaluate して値を取り出す。"""
    adef = default_registry.analysis_or_none(system, name)
    if adef is None:
        return {"error": f"analysis '{system}.{name}' not found"}

    if adef.system is None:
        import inspect

        sig = inspect.signature(adef.func)
        try:
            bound = sig.bind_partial(**payload)
            bound.apply_defaults()
        except TypeError as e:
            return {"error": f"argument error: {e}"}
        value = adef.func(*bound.args, **bound.kwargs)
        return {"value": to_jsonable(value)}

    return _run_veriq_node(adef.system, adef.name, verify=False)
