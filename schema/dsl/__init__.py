"""schema.dsl — user-facing DSL classes (Component / Config / Analysis)."""

from schema.dsl.analysis import analysis
from schema.dsl.component import Component
from schema.dsl.config import Config
from schema.dsl.placement import Placement
from schema.dsl.traits import (
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
