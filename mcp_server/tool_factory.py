"""Registry → MCP tool 定義の自動生成。

仕様: plan/Craft/01_仕様/MCP設計.md §2-3
MVP: 読み出し系 + analysis 実行のみ。書き込みは Phase 2。
"""

from collections.abc import Callable
from typing import Any

import mcp.types as mcp_types

from schema import default_registry


def build_tool_specs() -> list[mcp_types.Tool]:
    """registry を走査して MCP tool 定義を生成。"""
    tools: list[mcp_types.Tool] = []
    tools.extend(_introspection_tools())
    tools.extend(_component_read_tools())
    tools.extend(_config_read_tools())
    tools.extend(_analysis_tools())
    tools.extend(_verify_tools())
    tools.extend(_component_write_tools())
    tools.extend(_config_write_tools())
    tools.extend(_history_tools())
    return tools


# ─── introspection ─────────────────────────────────────────────────


def _introspection_tools() -> list[mcp_types.Tool]:
    empty_schema: dict[str, Any] = {"type": "object", "properties": {}}
    return [
        mcp_types.Tool(
            name="list_systems",
            description="登録済み system の一覧を返す。",
            inputSchema=empty_schema,
        ),
        mcp_types.Tool(
            name="list_components",
            description="全 component の (system, name, plural, cardinality, traits) を返す。",
            inputSchema=empty_schema,
        ),
        mcp_types.Tool(
            name="list_configs",
            description="全 config の (system, name) を返す。",
            inputSchema=empty_schema,
        ),
        mcp_types.Tool(
            name="list_analyses",
            description="全 @analysis の (system, name, verify, desc) を返す。",
            inputSchema=empty_schema,
        ),
        mcp_types.Tool(
            name="get_schema",
            description="component の JSON Schema (Entry model) を返す。",
            inputSchema={
                "type": "object",
                "properties": {
                    "system": {"type": "string"},
                    "component": {"type": "string"},
                },
                "required": ["system", "component"],
            },
        ),
    ]


# ─── component read ────────────────────────────────────────────────


def _component_read_tools() -> list[mcp_types.Tool]:
    out: list[mcp_types.Tool] = []
    for cdef in default_registry.components():
        if cdef.cardinality == "multi":
            out.append(
                mcp_types.Tool(
                    name=f"list_{cdef.plural}",
                    description=f"{cdef.system}.{cdef.name} の全インスタンス。",
                    inputSchema={"type": "object", "properties": {}},
                )
            )
            out.append(
                mcp_types.Tool(
                    name=f"get_{cdef.name}",
                    description=f"{cdef.system}.{cdef.name} の単一インスタンス（name 指定）。",
                    inputSchema={
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                )
            )
        else:
            out.append(
                mcp_types.Tool(
                    name=f"get_{cdef.name}",
                    description=f"{cdef.system}.{cdef.name} (Singleton) を取得。",
                    inputSchema={"type": "object", "properties": {}},
                )
            )
    return out


# ─── config read ───────────────────────────────────────────────────


def _config_read_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name=f"get_{cfg.name}",
            description=f"{cfg.system}.{cfg.name} (Config) を取得。",
            inputSchema={"type": "object", "properties": {}},
        )
        for cfg in default_registry.configs()
    ]


# ─── analysis ──────────────────────────────────────────────────────


def _analysis_tools() -> list[mcp_types.Tool]:
    out: list[mcp_types.Tool] = []
    for adef in default_registry.analyses():
        if adef.verify:
            continue  # verify_* は別系統
        prefix = "analyze"
        out.append(
            mcp_types.Tool(
                name=f"{prefix}_{adef.name}",
                description=adef.desc or f"Run analysis {adef.name}",
                inputSchema=_analysis_input_schema(adef),
            )
        )
    return out


def _analysis_input_schema(adef: Any) -> dict[str, Any]:
    """ad-hoc analysis のみ直接 input を受け取る。veriq 経由はデータ駆動。"""
    if adef.system is not None:
        return {"type": "object", "properties": {}}
    import inspect

    sig = inspect.signature(adef.func)
    props: dict[str, Any] = {}
    required: list[str] = []
    for param in sig.parameters.values():
        json_type = _python_to_json_type(param.annotation)
        props[param.name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(param.name)
    return {
        "type": "object",
        "properties": props,
        "required": required,
    }


def _python_to_json_type(annotation: Any) -> str:
    import inspect

    if annotation is inspect.Parameter.empty:
        return "string"
    if annotation is float:
        return "number"
    if annotation is int:
        return "integer"
    if annotation is bool:
        return "boolean"
    return "string"


# ─── verify ────────────────────────────────────────────────────────


def _verify_tools() -> list[mcp_types.Tool]:
    tools: list[mcp_types.Tool] = [
        mcp_types.Tool(
            name="verify_all",
            description="全 system の verification を実行。",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
    for adef in default_registry.analyses(verify=True):
        if adef.system is None:
            continue
        tools.append(
            mcp_types.Tool(
                name=f"verify_{adef.name}",
                description=adef.desc or f"Run verification {adef.name}",
                inputSchema={"type": "object", "properties": {}},
            )
        )
    return tools


# ─── component write ───────────────────────────────────────────────


def _component_write_tools() -> list[mcp_types.Tool]:
    out: list[mcp_types.Tool] = []
    for cdef in default_registry.components():
        if cdef.cardinality == "multi":
            out.append(
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
                )
            )
            out.append(
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
                )
            )
            out.append(
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
                )
            )
            out.append(
                mcp_types.Tool(
                    name=f"set_{cdef.plural}_spec",
                    description=(f"Replace the shared spec for {cdef.system}.{cdef.plural}."),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spec": {"type": "object"},
                            "etag": {"type": "string"},
                        },
                        "required": ["spec"],
                    },
                )
            )
        else:
            out.append(
                mcp_types.Tool(
                    name=f"patch_{cdef.name}",
                    description=(f"Partial update for {cdef.system}.{cdef.name} (Singleton)."),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "delta": {"type": "object"},
                            "etag": {"type": "string"},
                        },
                        "required": ["delta"],
                    },
                )
            )
    return out


# ─── config write ──────────────────────────────────────────────────


def _config_write_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name=f"set_{cfg.name}",
            description=f"Replace {cfg.system}.{cfg.name} (Config) contents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "object"},
                    "etag": {"type": "string"},
                },
                "required": ["data"],
            },
        )
        for cfg in default_registry.configs()
    ]


# ─── history / diff ────────────────────────────────────────────────


def _history_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="history",
            description="git log entries (optionally filtered by path / limit).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        ),
        mcp_types.Tool(
            name="diff",
            description="git diff between two refs (optional path filter).",
            inputSchema={
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["from", "to"],
            },
        ),
    ]


# ─── tool name → handler ────────────────────────────────────────────


def build_handler_map() -> dict[str, Callable[[dict[str, Any]], Any]]:
    """tool name → handler 関数の dict を返す。"""
    from mcp_server.handlers import (
        handle_analysis,
        handle_diff,
        handle_get_schema,
        handle_history,
        handle_list_introspection,
        handle_verify_all,
        handle_verify_single,
    )

    handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
        "list_systems": lambda _: handle_list_introspection("systems"),
        "list_components": lambda _: handle_list_introspection("components"),
        "list_configs": lambda _: handle_list_introspection("configs"),
        "list_analyses": lambda _: handle_list_introspection("analyses"),
        "get_schema": handle_get_schema,
        "verify_all": lambda _: handle_verify_all(),
        "history": handle_history,
        "diff": handle_diff,
    }
    for cdef in default_registry.components():
        if cdef.cardinality == "multi":
            handlers[f"list_{cdef.plural}"] = _make_list_handler(cdef.system, cdef.name)
            handlers[f"get_{cdef.name}"] = _make_get_multi_handler(cdef.system, cdef.name)
            handlers[f"add_{cdef.name}"] = _make_add_handler(cdef.system, cdef.name)
            handlers[f"patch_{cdef.name}"] = _make_patch_handler(cdef.system, cdef.name)
            handlers[f"delete_{cdef.name}"] = _make_delete_handler(cdef.system, cdef.name)
            handlers[f"set_{cdef.plural}_spec"] = _make_set_shared_spec_handler(
                cdef.system, cdef.name
            )
        else:
            handlers[f"get_{cdef.name}"] = _make_get_singleton_handler(cdef.system, cdef.name)
            handlers[f"patch_{cdef.name}"] = _make_patch_handler(cdef.system, cdef.name)
    for cfg in default_registry.configs():
        handlers[f"get_{cfg.name}"] = _make_get_config_handler(cfg.system, cfg.name)
        handlers[f"set_{cfg.name}"] = _make_set_config_handler(cfg.system, cfg.name)
    for adef in default_registry.analyses():
        if adef.verify:
            handlers[f"verify_{adef.name}"] = lambda _payload, name=adef.name, sub=adef.system: (
                handle_verify_single(sub, name)
            )
        else:
            handlers[f"analyze_{adef.name}"] = lambda payload, name=adef.name, sub=adef.system: (
                handle_analysis(sub, name, payload)
            )
    return handlers


def _make_list_handler(system: str, component: str):
    from mcp_server.handlers import handle_list_component_instances

    def h(_payload: dict[str, Any]) -> Any:
        return handle_list_component_instances(system, component)

    return h


def _make_get_multi_handler(system: str, component: str):
    from mcp_server.handlers import handle_get_component

    def h(payload: dict[str, Any]) -> Any:
        return handle_get_component(system, component, payload.get("name", ""))

    return h


def _make_get_singleton_handler(system: str, component: str):
    from mcp_server.handlers import handle_get_component

    def h(_payload: dict[str, Any]) -> Any:
        return handle_get_component(system, component, None)

    return h


def _make_get_config_handler(system: str, config_name: str):
    from mcp_server.handlers import handle_get_config

    def h(_payload: dict[str, Any]) -> Any:
        return handle_get_config(system, config_name)

    return h


def _make_add_handler(system: str, component: str):
    from mcp_server.handlers import handle_add_instance

    def h(payload: dict[str, Any]) -> Any:
        return handle_add_instance(system, component, payload)

    return h


def _make_patch_handler(system: str, component: str):
    from mcp_server.handlers import handle_patch_instance

    def h(payload: dict[str, Any]) -> Any:
        return handle_patch_instance(system, component, payload)

    return h


def _make_delete_handler(system: str, component: str):
    from mcp_server.handlers import handle_delete_instance

    def h(payload: dict[str, Any]) -> Any:
        return handle_delete_instance(system, component, payload)

    return h


def _make_set_shared_spec_handler(system: str, component: str):
    from mcp_server.handlers import handle_set_shared_spec

    def h(payload: dict[str, Any]) -> Any:
        return handle_set_shared_spec(system, component, payload)

    return h


def _make_set_config_handler(system: str, config_name: str):
    from mcp_server.handlers import handle_set_config

    def h(payload: dict[str, Any]) -> Any:
        return handle_set_config(system, config_name, payload)

    return h
