"""Craft schema — base classes for the typed declaration graph.

ユーザはここから `Component` / `Config` / `fld` / `analysis` を import する。
"""

from schema.codegen.root_model_builder import build_system_root_model
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
)
from schema.fields import fld
from schema.registry import (
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
