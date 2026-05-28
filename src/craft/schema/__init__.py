"""Craft schema — base classes for the typed declaration graph.

ユーザはここから `Component` / `Config` / `fld` / `analysis` を import する。
"""

from craft.schema.codegen.root_model_builder import build_system_root_model
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
)
from craft.schema.fields import fld
from craft.schema.registry import (
    AnalysisDefinition,
    ComponentDefinition,
    ConfigDefinition,
    UnifiedRegistry,
    default_registry,
)

__all__ = [
    "AnalysisDefinition",
    "Component",
    "ComponentDefinition",
    "Config",
    "ConfigDefinition",
    "MultiInstance",
    "Placeable",
    "Placement",
    "PowerConsuming",
    "SpecOnly",
    "TemperatureSensitive",
    "UnifiedRegistry",
    "analysis",
    "build_system_root_model",
    "default_registry",
    "fld",
]
