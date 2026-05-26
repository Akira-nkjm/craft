"""Config base class — 非 hardware 設定値（mission, orbit, environment 等）。"""

from typing import Any, ClassVar, dataclass_transform

from pydantic import BaseModel, ConfigDict, create_model

from schema.component import (
    _collect_fields_from,
    _infer_system_from_caller,
    _is_internal,
)
from schema.fields import fld
from schema.registry import ConfigDefinition, SourceLocation, default_registry


@dataclass_transform(field_specifiers=(fld,))
class Config:
    """全 config の基底クラス。常に Singleton。"""

    Model: ClassVar[type[BaseModel]]
    __system__: ClassVar[str]

    def __init_subclass__(
        cls,
        *,
        system: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if _is_internal(cls) or cls.__name__ == "Config":
            return

        if system is None:
            system = _infer_system_from_caller()

        fields = _collect_fields_from(cls)
        model_config = ConfigDict(extra="forbid")
        model = create_model(  # pyrefly: ignore[no-matching-overload]
            f"{cls.__name__}Model",
            __config__=model_config,
            **fields,
        )
        cls.Model = model
        cls.__system__ = system

        default_registry.register_config(
            ConfigDefinition(
                system=system,
                name=cls.__name__.lower(),
                model=model,
                cls=cls,
                source=SourceLocation.of(cls),
                desc=cls.__doc__,
            )
        )
