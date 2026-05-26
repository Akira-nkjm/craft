"""Scaffold engine — registry → data.toml 雛形（add-missing）。

仕様: plan/Craft/01_仕様/データパイプライン.md §4

実装:
- `tomlkit` 経由でコメントを保持
- 既存値は default で `--preserve-values`（破壊しない）
- `--format-only`: 既存値は触らず順序・コメントだけ整形
- `--overwrite`: 既存値も default に戻す（破壊的、確認は呼び元が責任）
- shared_spec=True (MultiInstance) → `<plural>.spec` 直下に spec を置く
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import tomlkit
from pydantic import BaseModel
from tomlkit import TOMLDocument
from tomlkit.items import Table

ScaffoldMode = Literal["add-missing", "overwrite", "format-only"]

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
    mode: ScaffoldMode = "add-missing"


def scaffold_system(
    system: str,
    *,
    dry_run: bool = False,
    mode: ScaffoldMode = "add-missing",
) -> tuple[ScaffoldResult, TOMLDocument]:
    """1 つの system の data.toml を雛形と diff merge する。

    Args:
        mode: "add-missing" (default) / "overwrite" (既存値を default に戻す) / "format-only" (整形のみ)

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

    for cdef in components:
        _scaffold_component(doc, cdef, added, removed, mode=mode)
    for cfg in configs:
        _scaffold_config(doc, cfg, added, removed, mode=mode)

    result = ScaffoldResult(
        system=system,
        file_path=data_path,
        written=not dry_run,
        added_paths=tuple(added),
        removed_warnings=tuple(removed),
        mode=mode,
    )

    if not dry_run:
        content = _normalize_scaffold_spacing(tomlkit.dumps(doc))
        write_toml_atomic(data_path, content)

    return result, doc


def scaffold_all(
    *,
    dry_run: bool = False,
    mode: ScaffoldMode = "add-missing",
) -> list[ScaffoldResult]:
    out: list[ScaffoldResult] = []
    for sub in sorted(default_registry.systems()):
        result, _ = scaffold_system(sub, dry_run=dry_run, mode=mode)
        out.append(result)
    return out


# ─── component / config 単位 ─────────────────────────────────────────


def _scaffold_component(
    target: TOMLDocument,
    cdef: ComponentDefinition,
    added: list[str],
    removed: list[str],
    *,
    mode: ScaffoldMode,
) -> None:
    if cdef.cardinality == "multi":
        _ensure_section_comment(target, cdef.plural, _class_name_to_title(cdef.cls))
        section = _ensure_table(target, cdef.plural)
        # MultiInstance の shared spec を `<plural>.spec` 直下に置く
        shared_spec_section = _ensure_table(section, "spec")
        _fill_model_section(
            shared_spec_section,
            cdef.spec,
            f"{cdef.plural}.spec",
            added,
            removed,
            mode=mode,
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
                mode=mode,
                include_spec=False,  # shared_spec のため per-instance spec は出さない
            )
    else:
        _ensure_section_comment(target, cdef.name, _class_name_to_title(cdef.cls))
        section = _ensure_table(target, cdef.name)
        _fill_instance_subsections(
            section,
            cdef,
            base_path=cdef.name,
            added=added,
            removed=removed,
            mode=mode,
            include_spec=True,
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
        spec_section = _ensure_table(section, "spec")
        _fill_model_section(
            spec_section,
            cdef.spec,
            f"{base_path}.spec",
            added,
            removed,
            mode=mode,
        )
    if cdef.design is not None:
        design_section = _ensure_table(section, "design")
        _fill_model_section(
            design_section,
            cdef.design,
            f"{base_path}.design",
            added,
            removed,
            mode=mode,
        )
    if cdef.requirements is not None:
        req_section = _ensure_table(section, "requirements")
        _fill_model_section(
            req_section,
            cdef.requirements,
            f"{base_path}.requirements",
            added,
            removed,
            mode=mode,
        )


def _scaffold_config(
    target: TOMLDocument,
    cfg: ConfigDefinition,
    added: list[str],
    removed: list[str],
    *,
    mode: ScaffoldMode,
) -> None:
    if cfg.cardinality == "multi":
        _ensure_section_comment(target, cfg.plural, _class_name_to_title(cfg.cls))
        section = _ensure_table(target, cfg.plural)
        instance_keys = [k for k in section if isinstance(section[k], (dict, Table))]
        if not instance_keys:
            instance_keys = ["main"]
        for inst in instance_keys:
            inst_section = _ensure_table(section, inst)
            _fill_model_section(
                inst_section,
                cfg.model,
                f"{cfg.plural}.{inst}",
                added,
                removed,
                mode=mode,
            )
    else:
        _ensure_section_comment(target, cfg.name, _class_name_to_title(cfg.cls))
        section = _ensure_table(target, cfg.name)
        _fill_model_section(
            section,
            cfg.model,
            cfg.name,
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


def _apply_field_add_missing(
    section: Table,
    fname: str,
    finfo: Any,
    base_path: str,
    added: list[str],
) -> None:
    if fname in section:
        return
    default = default_value(finfo)
    if default is None:
        return
    section[fname] = default
    added.append(f"{base_path}.{fname}")


def _apply_field_overwrite(
    section: Table,
    fname: str,
    finfo: Any,
    base_path: str,
    added: list[str],
) -> None:
    if fname in section:
        section[fname] = default_value(finfo)
        added.append(f"{base_path}.{fname} (overwrite)")
    else:
        default = default_value(finfo)
        if default is None:
            return
        section[fname] = default
        added.append(f"{base_path}.{fname}")


def _apply_field_format_only(
    section: Table,
    fname: str,
    finfo: Any,
    base_path: str,
    added: list[str],
) -> None:
    pass  # value changes are never made in format-only mode


_FIELD_APPLIERS = {
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

        # Nested BaseModel field → recursive subsection
        nested = _extract_nested_model(finfo.annotation)
        if nested is not None:
            if fname not in section and mode == "format-only":
                continue
            subsection = _ensure_table(section, fname)
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

    # registry に無い field は警告のみ
    for fname in list(section.keys()):
        if fname not in expected and not _is_nested_table(section[fname]):
            removed.append(f"{base_path}.{fname}")

    # 整形: 順序・コメント・float 正規化
    order_fields_by_registry(section, model)
    apply_field_comments(section, model)
    normalize_float_values(section, model)


def _normalize_scaffold_spacing(content: str) -> str:
    """scaffold 後の TOML テキストの空行を正規化する（冪等）。

    - `[...]` ヘッダ直前: 1 空行
    - MultiInstance のインスタンス切り替わり直前: 2 空行
    - `# === ... ===` 直前: 3 空行
    """
    # [section] ヘッダ直前を 1 空行に統一
    content = re.sub(r"\n+(\[[^\]\n]+\])", lambda m: "\n\n" + m.group(1), content)
    # MultiInstance のインスタンス切り替わりを 2 空行に昇格
    content = _promote_instance_transitions(content)
    # # === ... === 直前を 3 空行に統一
    content = re.sub(r"\n+(# ===)", lambda m: "\n\n\n\n" + m.group(1), content)
    # ファイル先頭の余分な空行を除去
    content = content.lstrip("\n")
    return content


def _promote_instance_transitions(content: str) -> str:
    """[root.A.x] → [root.B.y] の境界（インスタンス切り替わり）を 2 空行に昇格する。"""
    lines = content.split("\n")
    result: list[str] = []
    prev_instance: tuple[str, str] | None = None  # (root, instance)

    for line in lines:
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            parts = m.group(1).split(".")
            if len(parts) >= 3:
                root, inst = parts[0], parts[1]
                if (
                    prev_instance is not None
                    and prev_instance[0] == root
                    and prev_instance[1] != inst
                ):
                    # インスタンス切り替わり: 末尾の空行を 2 行に揃える
                    while result and result[-1] == "":
                        result.pop()
                    result.append("")
                    result.append("")
                prev_instance = (root, inst)
            else:
                prev_instance = None
        result.append(line)

    return "\n".join(result)


def _class_name_to_title(cls: type) -> str:
    """CamelCase クラス名を単語スペース区切りに変換する。

    SunSenser → Sun Senser, OBC → OBC, MissionProfile → Mission Profile
    """
    name = cls.__name__
    # lowercase/digit の直後に uppercase が来たら空白を挿入
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    # 連続 uppercase の直後に uppercase+lowercase が来たら空白を挿入（例: OBCFoo → OBC Foo）
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return name


def _ensure_section_comment(parent: TOMLDocument, key: str, title: str | None = None) -> None:
    """parent 内の key 直前に '# === Title ===' コメントが無ければ挿入する。

    既にコメントがある場合（=== を含む）はスキップ。
    """
    if title is None:
        title = key.replace("_", " ").title()
    body = parent._body  # TOMLDocument は Container を直接継承するため _body を直接持つ
    # key のインデックスを探す
    key_idx = next(
        (i for i, (k, _) in enumerate(body) if k is not None and str(k) == key),
        None,
    )
    if key_idx is None:
        # 未登録セクション: 後で _ensure_table が追加するので、今は先行コメントだけ挿入
        # 空行数は _normalize_scaffold_spacing が統一するので nl は 1 つだけ追加
        parent.add(tomlkit.nl())
        parent.add(tomlkit.comment(f"=== {title} ==="))
        parent.add(tomlkit.nl())
        return

    # 直前に === コメントが既にあるか確認（空行数は text 正規化に任せる）
    from tomlkit.items import Comment as _Comment

    for i in range(key_idx - 1, -1, -1):
        k, v = body[i]
        if k is not None:
            break
        if isinstance(v, _Comment) and "===" in str(v):
            return  # 既にある

    # === コメント無し → 新規挿入: key_idx の直前に nl + comment + nl
    new_items = [
        (None, tomlkit.nl()),
        (None, tomlkit.comment(f"=== {title} ===")),
        (None, tomlkit.nl()),
    ]
    for i, item in enumerate(new_items):
        body.insert(key_idx + i, item)
    # _map のインデックスを挿入分だけシフト
    n = len(new_items)
    map_ = parent._map
    for mk in list(map_.keys()):
        idx = map_[mk]
        if isinstance(idx, tuple):
            map_[mk] = tuple(i + n if i >= key_idx else i for i in idx)
        elif isinstance(idx, int) and idx >= key_idx:
            map_[mk] = idx + n


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


def _is_nested_table(value: Any) -> bool:
    return isinstance(value, (dict, Table)) and bool(value)


def _ensure_nl_before_key(section: Table, key: str) -> None:
    """section 内の key 直前に空行（改行）が無ければ挿入する。key が未登録なら末尾に nl を追加。"""
    from tomlkit.items import Whitespace

    body = section.value._body
    key_idx = next(
        (i for i, (k, _) in enumerate(body) if k is not None and str(k) == key),
        None,
    )
    if key_idx is None:
        section.add(tomlkit.nl())
        return
    for i in range(key_idx - 1, -1, -1):
        k, v = body[i]
        if k is not None:
            break
        if isinstance(v, Whitespace) and "\n" in str(v):
            return
    body.insert(key_idx, (None, tomlkit.nl()))
    map_ = section.value._map
    for mk in list(map_.keys()):
        idx = map_[mk]
        if isinstance(idx, tuple):
            map_[mk] = tuple(i + 1 if i >= key_idx else i for i in idx)
        elif isinstance(idx, int) and idx >= key_idx:
            map_[mk] = idx + 1


def _ensure_table(parent: TOMLDocument | Table, key: str) -> Table:
    """parent[key] を Table として確保。既存値が table でなければ作り直す。"""
    if key in parent:
        existing = parent[key]
        if isinstance(existing, Table):
            return existing
    new_tbl = tomlkit.table()
    parent[key] = new_tbl
    return parent[key]  # type: ignore[return-value]
