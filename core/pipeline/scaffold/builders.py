"""Scaffold の component / config 単位の雛形ロジック。"""

from collections.abc import Callable
from typing import Any, Literal

import tomlkit
from pydantic import BaseModel
from tomlkit import TOMLDocument
from tomlkit.items import Table

from core.io.toml_formatter import (
    apply_field_comments,
    default_value,
    normalize_float_values,
    order_fields_by_registry,
)
from core.io.toml_io import read_toml_doc
from core.paths import system_data_path
from core.pipeline.scaffold.formatting import class_name_to_title
from core.pipeline.scaffold.tomlkit_helpers import (
    ensure_section_comment,
    ensure_table,
    is_nested_table,
)
from schema.registry import ComponentDefinition, ConfigDefinition

ScaffoldMode = Literal["add-missing", "overwrite", "format-only"]


def scaffold_component(
    target: TOMLDocument,
    cdef: ComponentDefinition,
    added: list[str],
    removed: list[str],
    *,
    mode: ScaffoldMode,
) -> None:
    if cdef.cardinality == "multi":
        ensure_section_comment(target, cdef.plural, class_name_to_title(cdef.cls))
        section = ensure_table(target, cdef.plural)
        # MultiInstance の shared spec を `<plural>.spec` 直下に置く
        shared_spec_section = ensure_table(section, "spec")
        _fill_model_section(
            shared_spec_section,
            cdef.spec,
            f"{cdef.plural}.spec",
            added,
            removed,
            mode=mode,
        )
        instance_keys = [
            k for k in section if k != "spec" and isinstance(section[k], (dict, Table))
        ]
        if not instance_keys:
            instance_keys = ["main"]
        for inst in instance_keys:
            inst_section = ensure_table(section, inst)
            _fill_instance_subsections(
                inst_section,
                cdef,
                base_path=f"{cdef.plural}.{inst}",
                added=added,
                removed=removed,
                mode=mode,
                include_spec=False,  # shared_spec のため per-instance spec は出さない
            )
    else:
        ensure_section_comment(target, cdef.name, class_name_to_title(cdef.cls))
        section = ensure_table(target, cdef.name)
        _fill_instance_subsections(
            section,
            cdef,
            base_path=cdef.name,
            added=added,
            removed=removed,
            mode=mode,
            include_spec=True,
        )


def scaffold_config(
    target: TOMLDocument,
    cfg: ConfigDefinition,
    added: list[str],
    removed: list[str],
    *,
    mode: ScaffoldMode,
) -> None:
    if cfg.cardinality == "multi":
        ensure_section_comment(target, cfg.plural, class_name_to_title(cfg.cls))
        section = ensure_table(target, cfg.plural)
        instance_keys = [k for k in section if isinstance(section[k], (dict, Table))]
        if not instance_keys:
            instance_keys = ["main"]
        for inst in instance_keys:
            inst_section = ensure_table(section, inst)
            _fill_model_section(
                inst_section,
                cfg.model,
                f"{cfg.plural}.{inst}",
                added,
                removed,
                mode=mode,
            )
    else:
        ensure_section_comment(target, cfg.name, class_name_to_title(cfg.cls))
        section = ensure_table(target, cfg.name)
        _fill_model_section(
            section,
            cfg.model,
            cfg.name,
            added,
            removed,
            mode=mode,
        )


def _fill_instance_subsections(
    section: Table,
    cdef: ComponentDefinition,
    *,
    base_path: str,
    added: list[str],
    removed: list[str],
    mode: ScaffoldMode,
    include_spec: bool,
) -> None:
    """1 instance の spec / design / requirements を埋める。"""
    if include_spec:
        spec_section = ensure_table(section, "spec")
        _fill_model_section(
            spec_section,
            cdef.spec,
            f"{base_path}.spec",
            added,
            removed,
            mode=mode,
        )
    if cdef.design is not None:
        design_section = ensure_table(section, "design")
        _fill_model_section(
            design_section,
            cdef.design,
            f"{base_path}.design",
            added,
            removed,
            mode=mode,
        )
    if cdef.requirements is not None:
        req_section = ensure_table(section, "requirements")
        _fill_model_section(
            req_section,
            cdef.requirements,
            f"{base_path}.requirements",
            added,
            removed,
            mode=mode,
        )


def _extract_nested_model(annotation: Any) -> type[BaseModel] | None:
    """annotation が BaseModel サブクラス（または X | None）ならそのクラスを返す。"""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    args = getattr(annotation, "__args__", None)
    if args:
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                return arg
    return None


# ─── per-mode field appliers ──────────────────────────────────────────


def _apply_field_add_missing(
    section: Table, fname: str, finfo: Any, base_path: str, added: list[str]
) -> None:
    if fname in section:
        return
    default = default_value(finfo)
    if default is None:
        return
    section[fname] = default
    added.append(f"{base_path}.{fname}")


def _apply_field_overwrite(
    section: Table, fname: str, finfo: Any, base_path: str, added: list[str]
) -> None:
    default = default_value(finfo)
    if default is None:
        return
    if fname in section:
        section[fname] = default
        added.append(f"{base_path}.{fname} (overwrite)")
        return
    section[fname] = default
    added.append(f"{base_path}.{fname}")


def _apply_field_format_only(
    section: Table, fname: str, finfo: Any, base_path: str, added: list[str]
) -> None:
    pass  # format-only never adds or modifies fields


_FIELD_APPLIERS: dict[
    ScaffoldMode,
    Callable[[Table, str, Any, str, list[str]], None],
] = {
    "add-missing": _apply_field_add_missing,
    "overwrite": _apply_field_overwrite,
    "format-only": _apply_field_format_only,
}


def _fill_model_section(
    section: Table,
    model: type[BaseModel],
    base_path: str,
    added: list[str],
    removed: list[str],
    *,
    mode: ScaffoldMode,
) -> None:
    """model.model_fields に対して section を整える。"""
    expected = set(model.model_fields.keys())
    apply_field = _FIELD_APPLIERS[mode]

    for fname, finfo in model.model_fields.items():
        _ks = (
            finfo.json_schema_extra.get("key_source")
            if isinstance(finfo.json_schema_extra, dict)
            else None
        )
        key_source = _ks if isinstance(_ks, str) else None
        if key_source is not None:
            _fill_keyed_dict(section, fname, key_source, base_path, added, mode=mode)
            continue

        nested = _extract_nested_model(finfo.annotation)
        if nested is not None:
            if fname not in section and mode == "format-only":
                continue
            subsection = ensure_table(section, fname)
            _fill_model_section(
                subsection,
                nested,
                f"{base_path}.{fname}",
                added,
                removed,
                mode=mode,
            )
            continue

        apply_field(section, fname, finfo, base_path, added)

    for fname in list(section.keys()):
        if fname not in expected and not is_nested_table(section[fname]):
            removed.append(f"{base_path}.{fname}")

    order_fields_by_registry(section, model)
    apply_field_comments(section, model)
    normalize_float_values(section, model)


def _fill_keyed_dict(
    section: Table,
    fname: str,
    key_source: str,
    base_path: str,
    added: list[str],
    *,
    mode: ScaffoldMode,
) -> None:
    """key_source が示す config の instance キーを dict フィールドに補完する。

    既存キーは触らず、不足しているキーだけ False で追加する。
    key_source 形式: "<system>.<config_plural>" (例: "mission.operation_mode_configs")
    """
    if mode == "format-only":
        return
    parts = key_source.split(".", 1)
    if len(parts) != 2:
        return
    system, config_plural = parts
    keys = _load_config_instance_keys(system, config_plural)
    if not keys:
        return
    if fname not in section:
        section[fname] = tomlkit.table()
    sub = section[fname]
    if not isinstance(sub, (dict, Table)):
        return
    for key in keys:
        if key not in sub:
            sub[key] = False
            added.append(f"{base_path}.{fname}.{key}")


def _load_config_instance_keys(system: str, config_plural: str) -> list[str]:
    """data.toml から config の instance キー一覧を返す。"""
    doc = read_toml_doc(system_data_path(system))
    section = doc.get(config_plural, {})
    if not isinstance(section, (dict, Table)):
        return []
    return [k for k in section if isinstance(section[k], (dict, Table))]
