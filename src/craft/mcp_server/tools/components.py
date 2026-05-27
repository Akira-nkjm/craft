"""Component ツール (read + write) の spec と handler。"""

from collections.abc import Callable
from functools import partial
from typing import Any

import mcp.types as mcp_types

from craft.mcp_server.handlers import (
    handle_add_instance,
    handle_delete_instance,
    handle_get_component,
    handle_list_component_instances,
    handle_patch_instance,
    handle_set_shared_spec,
)
from craft.schema import default_registry


def _list_instances(system: str, component: str, _payload: dict[str, Any]) -> Any:
    return handle_list_component_instances(system, component)


def _get_multi(system: str, component: str, payload: dict[str, Any]) -> Any:
    return handle_get_component(system, component, payload.get("name", ""))


def _get_singleton(system: str, component: str, _payload: dict[str, Any]) -> Any:
    return handle_get_component(system, component, None)


def specs() -> list[mcp_types.Tool]:
    out: list[mcp_types.Tool] = []
    for cdef in default_registry.components():
        if cdef.cardinality == "multi":
            out.extend(
                [
                    mcp_types.Tool(
                        name=f"list_{cdef.plural}",
                        description=f"{cdef.system}.{cdef.name} の全インスタンス。",
                        inputSchema={"type": "object", "properties": {}},
                    ),
                    mcp_types.Tool(
                        name=f"get_{cdef.name}",
                        description=f"{cdef.system}.{cdef.name} の単一インスタンス（name 指定）。",
                        inputSchema={
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"],
                        },
                    ),
                    mcp_types.Tool(
                        name=f"add_{cdef.name}",
                        description=f"Create a new {cdef.system}.{cdef.name} instance.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "design": {"type": "object"},
                                "requirements": {"type": "object"},
                                "meta": {"type": "object"},
                                "spec": {"type": "object"},
                            },
                            "required": ["name"],
                        },
                    ),
                    mcp_types.Tool(
                        name=f"patch_{cdef.name}",
                        description=(
                            f"Partial update for {cdef.system}.{cdef.name} instance "
                            "(name required, etag optional)."
                        ),
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "delta": {"type": "object"},
                                "etag": {"type": "string"},
                            },
                            "required": ["name", "delta"],
                        },
                    ),
                    mcp_types.Tool(
                        name=f"delete_{cdef.name}",
                        description=f"Delete a {cdef.system}.{cdef.name} instance.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "etag": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    ),
                    mcp_types.Tool(
                        name=f"set_{cdef.plural}_spec",
                        description=f"Replace the shared spec for {cdef.system}.{cdef.plural}.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "spec": {"type": "object"},
                                "etag": {"type": "string"},
                            },
                            "required": ["spec"],
                        },
                    ),
                ]
            )
        else:
            out.extend(
                [
                    mcp_types.Tool(
                        name=f"get_{cdef.name}",
                        description=f"{cdef.system}.{cdef.name} (Singleton) を取得。",
                        inputSchema={"type": "object", "properties": {}},
                    ),
                    mcp_types.Tool(
                        name=f"patch_{cdef.name}",
                        description=f"Partial update for {cdef.system}.{cdef.name} (Singleton).",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "delta": {"type": "object"},
                                "etag": {"type": "string"},
                            },
                            "required": ["delta"],
                        },
                    ),
                ]
            )
    return out


def handlers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    h: dict[str, Callable[[dict[str, Any]], Any]] = {}
    for cdef in default_registry.components():
        if cdef.cardinality == "multi":
            h[f"list_{cdef.plural}"] = partial(_list_instances, cdef.system, cdef.name)
            h[f"get_{cdef.name}"] = partial(_get_multi, cdef.system, cdef.name)
            h[f"add_{cdef.name}"] = partial(handle_add_instance, cdef.system, cdef.name)
            h[f"patch_{cdef.name}"] = partial(handle_patch_instance, cdef.system, cdef.name)
            h[f"delete_{cdef.name}"] = partial(handle_delete_instance, cdef.system, cdef.name)
            h[f"set_{cdef.plural}_spec"] = partial(handle_set_shared_spec, cdef.system, cdef.name)
        else:
            h[f"get_{cdef.name}"] = partial(_get_singleton, cdef.system, cdef.name)
            h[f"patch_{cdef.name}"] = partial(handle_patch_instance, cdef.system, cdef.name)
    return h
