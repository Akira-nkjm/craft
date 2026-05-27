"""Unified registry payload builders for CLI / API / MCP surfaces."""

from dataclasses import dataclass

from craft.schema import default_registry


@dataclass(frozen=True, slots=True)
class ComponentSummary:
    system: str
    name: str
    plural: str
    cardinality: str
    traits: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfigSummary:
    system: str
    name: str
    plural: str
    cardinality: str


@dataclass(frozen=True, slots=True)
class AnalysisSummary:
    system: str | None
    name: str
    verify: bool
    desc: str | None


def list_components_summary(system: str | None = None) -> list[ComponentSummary]:
    return [
        ComponentSummary(
            system=c.system,
            name=c.name,
            plural=c.plural,
            cardinality=c.cardinality,
            traits=c.traits,
        )
        for c in default_registry.components(system=system)
    ]


def list_configs_summary(system: str | None = None) -> list[ConfigSummary]:
    return [
        ConfigSummary(
            system=c.system,
            name=c.name,
            plural=c.plural,
            cardinality=c.cardinality,
        )
        for c in default_registry.configs(system=system)
    ]


def list_analyses_summary(system: str | None = None) -> list[AnalysisSummary]:
    return [
        AnalysisSummary(
            system=a.system,
            name=a.name,
            verify=a.verify,
            desc=a.desc,
        )
        for a in default_registry.analyses(system=system)
    ]
