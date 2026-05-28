"""schema パッケージ内部共有ヘルパ。

Component / Config / analysis の `__init_subclass__` / decorator が共通で使う
ユーティリティ群。schema パッケージ外からの import は想定していない。
"""

import inspect
import re
from pathlib import Path
from typing import Any, ClassVar, get_origin

from pydantic.fields import FieldInfo

from craft.schema.fields import fld

_RESERVED = {
    "Spec",
    "Design",
    "Requirements",
    "Entry",
    "__cardinality__",
    "__shared_spec_default__",
    "__trait_no_design__",
    "__trait_design_extra__",
    "__system__",
    "__plural__",
    # _Trait protocol ClassVars — excluded from spec field collection
    "cardinality",
    "design_extra",
    "spec_only",
}


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def is_trait(base: type) -> bool:
    """Component 派生ではない trait class か判定。"""
    from craft.schema.dsl.traits import _Trait

    return base is not _Trait and isinstance(base, type) and issubclass(base, _Trait)


def is_internal(cls: type) -> bool:
    """internal/base class はスキップ。クラス名が `"Component"` または `_` 始まりなら True。"""
    return cls.__name__ == "Component" or cls.__name__.startswith("_")


def infer_system_from_caller() -> str:
    """呼び出し元ファイルパスから system を推論。

    `.../systems/<name>/...` から `<name>` を取得。
    """
    frame = inspect.currentframe()
    try:
        while frame is not None:
            path = Path(frame.f_code.co_filename)
            parts = path.parts
            if "systems" in parts:
                idx = parts.index("systems")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
            frame = frame.f_back
    finally:
        del frame
    raise RuntimeError(
        "Cannot infer system from caller stack. Pass `system='...'` as a class keyword argument."
    )


def auto_pluralize(name: str) -> str:
    """単純な英語複数化。`Battery` → `batteries`、`OBC` → `obcs`。"""
    base = _camel_to_snake(name)
    if base.endswith("y") and not base.endswith(("ay", "ey", "iy", "oy", "uy")):
        return base[:-1] + "ies"
    if base.endswith(("s", "x", "z", "ch", "sh")):
        return base + "es"
    return base + "s"


def collect_fields_from(source: Any) -> dict[str, tuple[type, Any]]:
    """`source` (class) の annotations と class-level defaults から field 辞書を作る。

    戻り値は `create_model` 用の `{name: (type, default_or_FieldInfo)}` 形式。
    """
    anns = getattr(source, "__annotations__", {}) or {}
    fields: dict[str, tuple[type, Any]] = {}
    for fname, ftype in anns.items():
        if fname in _RESERVED or fname.startswith("_"):
            continue
        if get_origin(ftype) is ClassVar:
            continue
        default = source.__dict__.get(fname, ...)
        if isinstance(default, FieldInfo):
            fields[fname] = (ftype, default)
        elif default is ...:
            fields[fname] = (ftype, fld())
        else:
            fields[fname] = (ftype, fld(default=default))
    return fields
