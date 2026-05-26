"""Component base class.

`__init_subclass__` で派生クラスの作成を hook し、Pydantic の
Spec / Design / Requirements / Entry モデルを動的構築 + UnifiedRegistry へ登録する。
"""

import inspect
import re
from pathlib import Path
from typing import Any, ClassVar, dataclass_transform

from pydantic import BaseModel, ConfigDict, create_model
from pydantic.fields import FieldInfo

from schema.fields import fld
from schema.placement import Placement
from schema.registry import ComponentDefinition, SourceLocation, default_registry

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
}


def _is_trait(base: type) -> bool:
    """Component 派生ではない trait class か判定。"""
    from schema.traits import _Trait

    return base is not _Trait and isinstance(base, type) and issubclass(base, _Trait)


def _is_internal(cls: type) -> bool:
    """internal/base class はスキップ。"""
    return cls.__name__ == "Component" or cls.__name__.startswith("_")


def _infer_system_from_caller() -> str:
    """呼び出し元ファイルパスから system を推論。

    `.../systems/<name>/...` から `<name>` を取得。
    """
    frame = inspect.currentframe()
    while frame is not None:
        path = Path(frame.f_code.co_filename)
        parts = path.parts
        if "systems" in parts:
            idx = parts.index("systems")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        frame = frame.f_back
    raise RuntimeError(
        "Cannot infer system from caller stack. Pass `system='...'` as a class keyword argument."
    )


def _auto_pluralize(name: str) -> str:
    """単純な英語複数化。`Battery` → `batteries`、`OBC` → `obc`。"""
    base = _camel_to_snake(name)
    if base.endswith("y") and not base.endswith(("ay", "ey", "iy", "oy", "uy")):
        return base[:-1] + "ies"
    if base.endswith(("s", "x", "z", "ch", "sh")):
        return base + "es"
    return base + "s"


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _collect_fields_from(source: Any) -> dict[str, tuple[type, Any]]:
    """`source` (class) の annotations と class-level defaults から field 辞書を作る。

    戻り値は `create_model` 用の `{name: (type, default_or_FieldInfo)}` 形式。
    """
    anns = getattr(source, "__annotations__", {}) or {}
    fields: dict[str, tuple[type, Any]] = {}
    for fname, ftype in anns.items():
        if fname in _RESERVED or fname.startswith("_"):
            continue
        default = source.__dict__.get(fname, ...)
        if isinstance(default, FieldInfo):
            fields[fname] = (ftype, default)
        elif default is ...:
            fields[fname] = (ftype, fld())
        else:
            fields[fname] = (ftype, fld(default=default))
    return fields


def _resolve_annotations(cls: type) -> dict[str, Any]:
    """Python 3.14 の lazy annotations を解決。"""
    try:
        return inspect.get_annotations(cls, eval_str=True)
    except Exception:
        return getattr(cls, "__annotations__", {}) or {}


@dataclass_transform(field_specifiers=(fld,))
class Component:
    """全 component の基底クラス。decorator なしで使う。

    すべての Component に自動追加されるフィールド:
        Spec:   mass_kg   (float, kg)  — 質量
        Design: quantity  (int, ≥1)    — 搭載個数

    trait を追加すると以下のフィールドも自動追加される:
        PowerConsuming    → Spec: power_per_unit_w  / Design: power_modes
        TemperatureSensitive → Spec: temp_min_c, temp_max_c
    """

    # `__init_subclass__` が動的に Pydantic モデルを構築して書き換えるため、
    # 型ヒント上は Any にしておく（user 派生で `class Design: ...` 等を書ける）。
    Spec: ClassVar[Any]
    Design: ClassVar[Any]
    Requirements: ClassVar[Any]
    Entry: ClassVar[Any]
    __system__: ClassVar[str]
    __plural__: ClassVar[str]
    __cardinality__: ClassVar[str] = "single"

    def __init_subclass__(
        cls,
        *,
        system: str | None = None,
        plural: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if _is_internal(cls):
            return

        if system is None:
            system = _infer_system_from_caller()
        if plural is None:
            plural = _auto_pluralize(cls.__name__)

        cardinality = "single"
        spec_only = False
        traits: list[str] = []
        for base in cls.__mro__:
            if base is cls:
                continue
            if _is_trait(base):
                traits.append(base.__name__)
                if getattr(base, "__cardinality__", None) == "multi":
                    cardinality = "multi"
                if getattr(base, "__trait_no_design__", False):
                    spec_only = True

        # Spec fields: walk MRO from base→derived so derived overrides
        # mass_kg は全 component 共通の基底 spec フィールド（user が上書き可能）
        spec_fields: dict[str, tuple[type, Any]] = {
            "mass_kg": (float, fld(ge=0, default=0.0, unit="kg", desc="質量")),
        }
        design_extra: dict[str, tuple[type, Any]] = {}
        for base in reversed(cls.__mro__):
            if base is object or base is Component:
                continue
            spec_fields.update(_collect_fields_from(base))
            extra = base.__dict__.get("__trait_design_extra__")
            if extra:
                design_extra.update(extra)

        # Inner Design / Requirements classes
        inner_design = cls.__dict__.get("Design")
        inner_req = cls.__dict__.get("Requirements")

        # quantity / placement は全 component 共通の基底 design フィールド（user が上書き可能）
        design_fields: dict[str, tuple[type, Any]] = {
            "quantity": (int, fld(ge=1, default=1, desc="搭載個数")),
            "placement": (Placement | None, fld(default=None, desc="搭載位置・CAD パラメータ")),
        }
        design_fields.update(design_extra)
        if inner_design is not None:
            design_fields.update(_collect_fields_from(inner_design))

        req_fields: dict[str, tuple[type, Any]] = {}
        if inner_req is not None:
            req_fields.update(_collect_fields_from(inner_req))

        model_config = ConfigDict(extra="forbid")
        # pyrefly: pydantic.create_model の overload は **dict 展開と相性が悪い
        spec_model = create_model(  # pyrefly: ignore[no-matching-overload]
            f"{cls.__name__}Spec",
            __config__=model_config,
            **spec_fields,
        )
        if spec_only:
            design_model: type[BaseModel] | None = None
        else:
            design_model = create_model(  # pyrefly: ignore[no-matching-overload]
                f"{cls.__name__}Design",
                __config__=model_config,
                **design_fields,
            )
        req_model: type[BaseModel] | None = None
        if req_fields:
            req_model = create_model(  # pyrefly: ignore[no-matching-overload]
                f"{cls.__name__}Requirements",
                __config__=model_config,
                **req_fields,
            )

        entry_fields: dict[str, tuple[Any, Any]] = {
            "spec": (spec_model, fld()),
        }
        if design_model is not None:
            entry_fields["design"] = (
                design_model,
                fld(default_factory=design_model),
            )
        if req_model is not None:
            entry_fields["requirements"] = (
                req_model,
                fld(default_factory=req_model),
            )
        entry_fields["meta"] = (dict[str, Any] | None, fld(default=None))

        entry_model = create_model(  # pyrefly: ignore[no-matching-overload]
            f"{cls.__name__}Entry",
            __config__=ConfigDict(extra="forbid"),
            **entry_fields,
        )

        cls.Spec = spec_model
        cls.Design = design_model
        cls.Requirements = req_model
        cls.Entry = entry_model
        cls.__system__ = system
        cls.__plural__ = plural
        cls.__cardinality__ = cardinality

        default_registry.register_component(
            ComponentDefinition(
                system=system,
                name=cls.__name__.lower(),
                plural=plural,
                cardinality=cardinality,
                spec=spec_model,
                design=design_model,
                requirements=req_model,
                entry=entry_model,
                cls=cls,
                traits=tuple(traits),
                source=SourceLocation.of(cls),
                desc=cls.__doc__,
            )
        )
