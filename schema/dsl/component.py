"""Component base class.

`__init_subclass__` で派生クラスの作成を hook し、Pydantic の
Spec / Design / Requirements / Entry モデルを動的構築 + UnifiedRegistry へ登録する。
"""

from typing import Any, ClassVar, dataclass_transform

from pydantic import BaseModel, ConfigDict, create_model

from schema._subclass_helpers import (
    auto_pluralize,
    collect_fields_from,
    infer_system_from_caller,
    is_internal,
    is_trait,
)
from schema.fields import fld
from schema.registry import ComponentDefinition, SourceLocation, default_registry


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
        if is_internal(cls):
            return

        if system is None:
            system = infer_system_from_caller()
        if plural is None:
            plural = auto_pluralize(cls.__name__)

        cardinality = "single"
        spec_only = False
        traits: list[str] = []
        for base in cls.__mro__:
            if base is cls:
                continue
            if is_trait(base):
                traits.append(base.__name__)
                if getattr(base, "cardinality", "single") == "multi":
                    cardinality = "multi"
                if getattr(base, "spec_only", False):
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
            spec_fields.update(collect_fields_from(base))
            extra = base.__dict__.get("design_extra")
            if extra:
                design_extra.update(extra)

        # Inner Design / Requirements classes
        inner_design = cls.__dict__.get("Design")
        inner_req = cls.__dict__.get("Requirements")

        # quantity は全 component 共通の基底 design フィールド（user が上書き可能）
        # placement は Placeable trait で opt-in する
        design_fields: dict[str, tuple[type, Any]] = {
            "quantity": (int, fld(ge=1, default=1, desc="搭載個数")),
        }
        design_fields.update(design_extra)
        if inner_design is not None:
            design_fields.update(collect_fields_from(inner_design))

        req_fields: dict[str, tuple[type, Any]] = {}
        if inner_req is not None:
            req_fields.update(collect_fields_from(inner_req))

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
