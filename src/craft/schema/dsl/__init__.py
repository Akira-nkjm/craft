"""schema.dsl — user-facing DSL classes (Component / Config / Analysis)."""

from craft.schema.dsl.analysis import analysis
from craft.schema.dsl.component import Component
from craft.schema.dsl.config import Config
from craft.schema.dsl.placement import Placement
from craft.schema.dsl.traits import (
    MultiInstance,
    Placeable,
    PowerConsuming,
    SpecOnly,
    TemperatureSensitive,
    _Trait,
)

__all__ = [
    "Component",
    "Config",
    "MultiInstance",
    "Placeable",
    "Placement",
    "PowerConsuming",
    "SpecOnly",
    "TemperatureSensitive",
    "_Trait",
    "analysis",
]
