"""Config base class — 非 hardware 設定値（mission, orbit, environment 等）。"""

from typing import Any, ClassVar, dataclass_transform

from pydantic import BaseModel, ConfigDict, create_model

from schema.component import (
    _auto_pluralize,
    _collect_fields_from,
    _infer_system_from_caller,
    _is_internal,
    _is_trait,
)
from schema.fields import fld
from schema.registry import ConfigDefinition, SourceLocation, default_registry


@dataclass_transform(field_specifiers=(fld,))
class Config:
    """全 config の基底クラス。Singleton または MultiInstance。"""

    Model: ClassVar[type[BaseModel]]
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
        if _is_internal(cls) or cls.__name__ == "Config":
            return

        if system is None:
            system = _infer_system_from_caller()

        cardinality = "single"
        for base in cls.__mro__:
            if base is cls:
                continue
            if _is_trait(base) and getattr(base, "cardinality", "single") == "multi":
                cardinality = "multi"

        if plural is None:
            plural = _auto_pluralize(cls.__name__)

        fields = _collect_fields_from(cls)
        model_config = ConfigDict(extra="forbid")
        model = create_model(  # pyrefly: ignore[no-matching-overload]
            f"{cls.__name__}Model",
            __config__=model_config,
            **fields,
        )
        cls.Model = model
        cls.__system__ = system
        cls.__plural__ = plural
        cls.__cardinality__ = cardinality

        default_registry.register_config(
            ConfigDefinition(
                system=system,
                name=cls.__name__.lower(),
                plural=plural,
                cardinality=cardinality,
                model=model,
                cls=cls,
                source=SourceLocation.of(cls),
                desc=cls.__doc__,
            )
        )
