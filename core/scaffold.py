"""Scaffold engine — registry → data.toml 雛形（add-missing）。

仕様: plan/Craft/01_仕様/データパイプライン.md §4

実装:
- `tomlkit` 経由でコメントを保持
- 既存値は default で `--preserve-values`（破壊しない）
- `--format-only`: 既存値は触らず順序・コメントだけ整形
- `--overwrite`: 既存値も default に戻す（破壊的、確認は呼び元が責任）
- shared_spec=True (MultiInstance) → `<plural>.spec` 直下に spec を置く
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit
from pydantic import BaseModel
from tomlkit import TOMLDocument
from tomlkit.items import Table

from core.paths import system_data_path
from core.toml_formatter import (
    apply_field_comments,
    default_value,
    normalize_float_values,
    order_fields_by_registry,
)
from core.toml_io import read_toml_doc, write_toml_atomic
from schema import default_registry
from schema.registry import ComponentDefinition, ConfigDefinition


@dataclass(frozen=True, slots=True)
class ScaffoldResult:
    system: str
    file_path: Path
    written: bool
    added_paths: tuple[str, ...] = ()
    removed_warnings: tuple[str, ...] = field(default_factory=tuple)
    mode: str = "add-missing"


def scaffold_system(
    system: str,
    *,
    dry_run: bool = False,
    format_only: bool = False,
    overwrite: bool = False,
) -> tuple[ScaffoldResult, TOMLDocument]:
    """1 つの system の data.toml を雛形と diff merge する。

    Args:
        format_only: 既存値を触らず順序・コメントのみ整形
        overwrite: 既存値を default に戻す（破壊的）

    Returns:
        (result, updated TOMLDocument)
    """
    components = default_registry.components(system=system)
    configs = default_registry.configs(system=system)
    if not components and not configs:
        raise ValueError(f"No components/configs registered for system '{system}'")

    data_path = system_data_path(system)
    doc = read_toml_doc(data_path)

    added: list[str] = []
    removed: list[str] = []
    mode = "format-only" if format_only else ("overwrite" if overwrite else "add-missing")

    for cdef in components:
        _scaffold_component(doc, cdef, added, removed, format_only=format_only, overwrite=overwrite)
    for cfg in configs:
        _scaffold_config(doc, cfg, added, removed, format_only=format_only, overwrite=overwrite)

    result = ScaffoldResult(
        system=system,
        file_path=data_path,
        written=not dry_run,
        added_paths=tuple(added),
        removed_warnings=tuple(removed),
        mode=mode,
    )

    if not dry_run:
        write_toml_atomic(data_path, doc)

    return result, doc


def scaffold_all(
    *,
    dry_run: bool = False,
    format_only: bool = False,
    overwrite: bool = False,
) -> list[ScaffoldResult]:
    out: list[ScaffoldResult] = []
    for sub in sorted(default_registry.systems()):
        result, _ = scaffold_system(
            sub, dry_run=dry_run, format_only=format_only, overwrite=overwrite
        )
        out.append(result)
    return out


# ─── component / config 単位 ─────────────────────────────────────────


def _scaffold_component(
    target: TOMLDocument,
    cdef: ComponentDefinition,
    added: list[str],
    removed: list[str],
    *,
    format_only: bool,
    overwrite: bool,
) -> None:
    if cdef.cardinality == "multi":
        section = _ensure_table(target, cdef.plural)
        # MultiInstance の shared spec を `<plural>.spec` 直下に置く
        shared_spec_section = _ensure_table(section, "spec")
        _fill_model_section(
            shared_spec_section,
            cdef.spec,
            f"{cdef.plural}.spec",
            added,
            removed,
            format_only=format_only,
            overwrite=overwrite,
        )
        # 既存 instance キー or default placeholder
        instance_keys = [
            k for k in section if k != "spec" and isinstance(section[k], (dict, Table))
        ]
        if not instance_keys:
            instance_keys = ["main"]
        for inst in instance_keys:
            inst_section = _ensure_table(section, inst)
            _fill_instance_subsections(
                inst_section,
                cdef,
                base_path=f"{cdef.plural}.{inst}",
                added=added,
                removed=removed,
                format_only=format_only,
                overwrite=overwrite,
                include_spec=False,  # shared_spec のため per-instance spec は出さない
            )
    else:
        section = _ensure_table(target, cdef.name)
        _fill_instance_subsections(
            section,
            cdef,
            base_path=cdef.name,
            added=added,
            removed=removed,
            format_only=format_only,
            overwrite=overwrite,
            include_spec=True,
        )


def _fill_instance_subsections(
    section: Table,
    cdef: ComponentDefinition,
    *,
    base_path: str,
    added: list[str],
    removed: list[str],
    format_only: bool,
    overwrite: bool,
    include_spec: bool,
) -> None:
    """1 instance の spec / design / requirements を埋める。"""
    if include_spec:
        spec_section = _ensure_table(section, "spec")
        _fill_model_section(
            spec_section,
            cdef.spec,
            f"{base_path}.spec",
            added,
            removed,
            format_only=format_only,
            overwrite=overwrite,
        )
    if cdef.design is not None:
        design_section = _ensure_table(section, "design")
        _fill_model_section(
            design_section,
            cdef.design,
            f"{base_path}.design",
            added,
            removed,
            format_only=format_only,
            overwrite=overwrite,
        )
    if cdef.requirements is not None:
        req_section = _ensure_table(section, "requirements")
        _fill_model_section(
            req_section,
            cdef.requirements,
            f"{base_path}.requirements",
            added,
            removed,
            format_only=format_only,
            overwrite=overwrite,
        )


def _scaffold_config(
    target: TOMLDocument,
    cfg: ConfigDefinition,
    added: list[str],
    removed: list[str],
    *,
    format_only: bool,
    overwrite: bool,
) -> None:
    section = _ensure_table(target, cfg.name)
    _fill_model_section(
        section,
        cfg.model,
        cfg.name,
        added,
        removed,
        format_only=format_only,
        overwrite=overwrite,
    )


def _fill_model_section(
    section: Table,
    model: type[BaseModel],
    base_path: str,
    added: list[str],
    removed: list[str],
    *,
    format_only: bool,
    overwrite: bool,
) -> None:
    """model.model_fields に対して section を整える。"""
    expected = set(model.model_fields.keys())

    for fname, finfo in model.model_fields.items():
        if fname in section:
            if overwrite:
                section[fname] = default_value(finfo)
                added.append(f"{base_path}.{fname} (overwrite)")
            # format_only か add-missing で既存値がある場合は触らない
            continue
        if format_only:
            continue
        default = default_value(finfo)
        if default is None:
            continue
        section[fname] = default
        added.append(f"{base_path}.{fname}")

    # registry に無い field は警告のみ
    for fname in list(section.keys()):
        if fname not in expected and not _is_nested_table(section[fname]):
            removed.append(f"{base_path}.{fname}")

    # 整形: 順序・コメント・float 正規化
    order_fields_by_registry(section, model)
    apply_field_comments(section, model)
    normalize_float_values(section, model)


def _is_nested_table(value: Any) -> bool:
    return isinstance(value, (dict, Table)) and bool(value)


def _ensure_table(parent: TOMLDocument | Table, key: str) -> Table:
    """parent[key] を Table として確保。既存値が table でなければ作り直す。"""
    if key in parent:
        existing = parent[key]
        if isinstance(existing, Table):
            return existing
    new_tbl = tomlkit.table()
    parent[key] = new_tbl
    return parent[key]  # type: ignore[return-value]
