"""Subsystem root model 動的構築。

`build_subsystem_root_model(subsystem, data_path)`:
1. registry の `subsystem` 配下の component / config を走査
2. 各 MultiInstance component の `plural` をキーに `vq.Table[NameEnum, Entry]`、
   Singleton component には `<name>: Entry`、Config には `<name>: Model` を生やす
3. instance キーの enum (`<Plural>Name`) は data.toml の現在キーから動的構築
4. shared_spec=True に対応:
   - TOML 上 `[<plural>.spec]` 直下に共有 spec を書く
   - `model_validator(mode="before")` が各 instance に shared spec を伝播
"""

import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Any

import veriq as vq
from pydantic import BaseModel, ConfigDict, create_model, model_validator

from schema.registry import default_registry

# 個別 instance キーとして扱わない予約語
_RESERVED_KEYS = {"spec"}


def _load_instance_keys(data_path: Path, plural: str) -> list[str]:
    """data.toml (簡略形式) から `[<plural>.<key>...]` の instance `<key>` 一覧を返す。

    `spec` (shared_spec の置き場) は除外する。
    """
    if not data_path.exists():
        return []
    with data_path.open("rb") as f:
        data = tomllib.load(f)
    section = data.get(plural, {})
    if not isinstance(section, dict):
        return []
    return [k for k in section if k not in _RESERVED_KEYS and isinstance(section[k], dict)]


def _make_name_enum(plural: str, keys: list[str]) -> type[StrEnum]:
    """`<Plural>Name` という StrEnum を keys から動的構築。"""
    enum_name = "".join(p.capitalize() for p in plural.split("_")) + "Name"
    if not keys:
        keys = ["_empty"]
    return StrEnum(enum_name, {k.upper(): k for k in keys})  # pyrefly: ignore[bad-return]


def _make_root_base(multi_plurals: list[str]) -> type[BaseModel]:
    """shared_spec を各 instance に伝播する model_validator を持つ base class。"""

    class _RootBase(BaseModel):
        model_config = ConfigDict(extra="forbid")

        @model_validator(mode="before")
        @classmethod
        def _fan_out_shared_spec(cls, data: Any) -> Any:
            if not isinstance(data, dict):
                return data
            out = dict(data)
            for plural in multi_plurals:
                group = out.get(plural)
                if not isinstance(group, dict) or "spec" not in group:
                    continue
                shared = group["spec"]
                # spec 自体は instance ではないので除去
                new_group = {k: v for k, v in group.items() if k != "spec"}
                for inst_name, inst_data in list(new_group.items()):
                    if not isinstance(inst_data, dict):
                        continue
                    if "spec" not in inst_data:
                        # shared spec を浅いコピーで配布
                        inst_data["spec"] = dict(shared) if isinstance(shared, dict) else shared
                    new_group[inst_name] = inst_data
                out[plural] = new_group
            return out

    return _RootBase


def build_subsystem_root_model(subsystem: str, data_path: Path) -> type[BaseModel]:
    """subsystem 配下の component / config から root model を組み立てる。"""
    components = default_registry.components(subsystem=subsystem)
    configs = default_registry.configs(subsystem=subsystem)

    fields: dict[str, tuple[Any, Any]] = {}
    multi_plurals: list[str] = []

    for cdef in components:
        if cdef.cardinality == "multi":
            keys = _load_instance_keys(data_path, cdef.plural)
            name_enum = _make_name_enum(cdef.plural, keys)
            table_type = vq.Table[name_enum, cdef.entry]
            fields[cdef.plural] = (table_type, ...)
            multi_plurals.append(cdef.plural)
        else:
            fields[cdef.name] = (cdef.entry, ...)

    for cfg in configs:
        fields[cfg.name] = (cfg.model, ...)

    model_name = f"{subsystem.capitalize()}RootModel"
    base_cls = _make_root_base(multi_plurals)
    return create_model(  # pyrefly: ignore[no-matching-overload]
        model_name,
        __base__=base_cls,
        **fields,
    )
