"""Config ツール (read + write) の spec と handler。"""

from collections.abc import Callable
from functools import partial
from typing import Any

import mcp.types as mcp_types

from craft.mcp_server.handlers import (
    handle_delete_config_instance,
    handle_get_config,
    handle_get_config_instance,
    handle_patch_config_instance,
    handle_set_config,
    handle_set_config_instance,
)
from craft.schema import default_registry


def _get_singleton_config(system: str, name: str, _payload: dict[str, Any]) -> Any:
    return handle_get_config(system, name)


def _get_config_instance(system: str, name: str, payload: dict[str, Any]) -> Any:
    return handle_get_config_instance(system, name, payload.get("key", ""))


def specs() -> list[mcp_types.Tool]:
    out: list[mcp_types.Tool] = []
    for cfg in default_registry.configs():
        if cfg.cardinality == "multi":
            out.extend(
                [
                    mcp_types.Tool(
                        name=f"list_{cfg.plural}",
                        description=f"{cfg.system}.{cfg.name} の全エントリ一覧。",
                        inputSchema={"type": "object", "properties": {}},
                    ),
                    mcp_types.Tool(
                        name=f"get_{cfg.name}",
                        description=f"{cfg.system}.{cfg.name} の1エントリを key で取得。",
                        inputSchema={
                            "type": "object",
                            "properties": {"key": {"type": "string"}},
                            "required": ["key"],
                        },
                    ),
                    mcp_types.Tool(
                        name=f"set_{cfg.name}",
                        description=f"{cfg.system}.{cfg.name} エントリを作成または全置換。",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "data": {"type": "object"},
                                "etag": {"type": "string"},
                            },
                            "required": ["key", "data"],
                        },
                    ),
                    mcp_types.Tool(
                        name=f"patch_{cfg.name}",
                        description=f"{cfg.system}.{cfg.name} エントリを部分更新。",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "delta": {"type": "object"},
                                "etag": {"type": "string"},
                            },
                            "required": ["key", "delta"],
                        },
                    ),
                    mcp_types.Tool(
                        name=f"delete_{cfg.name}",
                        description=f"{cfg.system}.{cfg.name} エントリを削除。",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "etag": {"type": "string"},
                            },
                            "required": ["key"],
                        },
                    ),
                ]
            )
        else:
            out.extend(
                [
                    mcp_types.Tool(
                        name=f"get_{cfg.name}",
                        description=f"{cfg.system}.{cfg.name} (Config) を取得。",
                        inputSchema={"type": "object", "properties": {}},
                    ),
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
                    ),
                ]
            )
    return out


def handlers() -> dict[str, Callable[[dict[str, Any]], Any]]:
    h: dict[str, Callable[[dict[str, Any]], Any]] = {}
    for cfg in default_registry.configs():
        if cfg.cardinality == "multi":
            h[f"list_{cfg.plural}"] = partial(_get_singleton_config, cfg.system, cfg.name)
            h[f"get_{cfg.name}"] = partial(_get_config_instance, cfg.system, cfg.name)
            h[f"set_{cfg.name}"] = partial(handle_set_config_instance, cfg.system, cfg.name)
            h[f"patch_{cfg.name}"] = partial(handle_patch_config_instance, cfg.system, cfg.name)
            h[f"delete_{cfg.name}"] = partial(handle_delete_config_instance, cfg.system, cfg.name)
        else:
            h[f"get_{cfg.name}"] = partial(_get_singleton_config, cfg.system, cfg.name)
            h[f"set_{cfg.name}"] = partial(handle_set_config, cfg.system, cfg.name)
    return h
