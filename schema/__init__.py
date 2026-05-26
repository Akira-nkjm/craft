"""Craft schema — base classes for the typed declaration graph.

ユーザはここから `Component` / `Config` / `fld` / `analysis` を import する。
"""

from schema.analysis import analysis
from schema.component import Component
from schema.config import Config
from schema.fields import fld
from schema.registry import (
    AnalysisDefinition,
    ComponentDefinition,
    ConfigDefinition,
    UnifiedRegistry,
    default_registry,
)
from schema.root_model_builder import build_system_root_model
from schema.traits import (
    MultiInstance,
    PowerConsuming,
    SpecOnly,
    TemperatureSensitive,
)

__all__ = [
    "AnalysisDefinition",
    "Component",
    "ComponentDefinition",
    "Config",
    "ConfigDefinition",
    "MultiInstance",
    "PowerConsuming",
    "SpecOnly",
    "TemperatureSensitive",
    "UnifiedRegistry",
    "analysis",
    "build_system_root_model",
    "default_registry",
    "fld",
]
