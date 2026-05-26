"""UnifiedRegistry — 全 decorator / base class の唯一の登録先。"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """定義箇所のファイル・行・モジュール。"""

    file: str
    line: int
    module: str

    @classmethod
    def of(cls, obj: Any) -> "SourceLocation":  # noqa: UP037
        import inspect

        try:
            file = inspect.getsourcefile(obj) or "<unknown>"
            _, line = inspect.getsourcelines(obj)
        except TypeError, OSError:
            file = "<unknown>"
            line = 0
        module = getattr(obj, "__module__", "<unknown>")
        return cls(file=file, line=line, module=module)


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    subsystem: str
    name: str
    plural: str
    cardinality: str
    spec: type[BaseModel]
    design: type[BaseModel] | None
    requirements: type[BaseModel] | None
    entry: type[BaseModel]
    cls: type
    traits: tuple[str, ...]
    source: SourceLocation
    desc: str | None = None


@dataclass(frozen=True, slots=True)
class ConfigDefinition:
    subsystem: str
    name: str
    model: type[BaseModel]
    cls: type
    source: SourceLocation
    desc: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisDefinition:
    name: str
    subsystem: str | None
    func: Callable[..., Any]
    verify: bool
    imports: tuple[str, ...]
    cache: bool
    source: SourceLocation
    desc: str | None = None


class RegistryError(Exception):
    """Registry 系の基底例外。"""


class DuplicateRegistration(RegistryError):  # noqa: N818
    """同じキーで二重登録された。"""


class NotRegistered(RegistryError):  # noqa: N818
    """要求された定義が見つからない。"""


@dataclass
class UnifiedRegistry:
    """Components / Configs / Analyses を一括管理。"""

    _components: dict[tuple[str, str], ComponentDefinition] = field(default_factory=dict)
    _configs: dict[tuple[str, str], ConfigDefinition] = field(default_factory=dict)
    _analyses: dict[tuple[str | None, str], AnalysisDefinition] = field(default_factory=dict)

    def register_component(self, defn: ComponentDefinition) -> None:
        key = (defn.subsystem, defn.name)
        if key in self._components:
            raise DuplicateRegistration(
                f"Component {defn.subsystem}.{defn.name} already registered"
            )
        # plural 衝突検出
        for existing in self._components.values():
            if existing.subsystem == defn.subsystem and existing.plural == defn.plural:
                raise DuplicateRegistration(
                    f"Plural '{defn.plural}' already used by {existing.subsystem}.{existing.name}"
                )
        self._components[key] = defn

    def register_config(self, defn: ConfigDefinition) -> None:
        key = (defn.subsystem, defn.name)
        if key in self._configs:
            raise DuplicateRegistration(f"Config {defn.subsystem}.{defn.name} already registered")
        self._configs[key] = defn

    def register_analysis(self, defn: AnalysisDefinition) -> None:
        key = (defn.subsystem, defn.name)
        if key in self._analyses:
            raise DuplicateRegistration(f"Analysis {defn.subsystem}.{defn.name} already registered")
        self._analyses[key] = defn

    def component(self, subsystem: str, name: str) -> ComponentDefinition:
        try:
            return self._components[(subsystem, name)]
        except KeyError as err:
            raise NotRegistered(f"Component {subsystem}.{name}") from err

    def component_or_none(self, subsystem: str, name: str) -> ComponentDefinition | None:
        return self._components.get((subsystem, name))

    def components(self, *, subsystem: str | None = None) -> list[ComponentDefinition]:
        defs = list(self._components.values())
        if subsystem is not None:
            defs = [d for d in defs if d.subsystem == subsystem]
        return defs

    def config(self, subsystem: str, name: str) -> ConfigDefinition:
        try:
            return self._configs[(subsystem, name)]
        except KeyError as err:
            raise NotRegistered(f"Config {subsystem}.{name}") from err

    def configs(self, *, subsystem: str | None = None) -> list[ConfigDefinition]:
        defs = list(self._configs.values())
        if subsystem is not None:
            defs = [d for d in defs if d.subsystem == subsystem]
        return defs

    def analysis(self, subsystem: str | None, name: str) -> AnalysisDefinition:
        try:
            return self._analyses[(subsystem, name)]
        except KeyError as err:
            raise NotRegistered(f"Analysis {subsystem}.{name}") from err

    def analysis_or_none(self, subsystem: str | None, name: str) -> AnalysisDefinition | None:
        return self._analyses.get((subsystem, name))

    def analyses(
        self,
        *,
        subsystem: str | None = None,
        verify: bool | None = None,
    ) -> list[AnalysisDefinition]:
        defs = list(self._analyses.values())
        if subsystem is not None:
            defs = [d for d in defs if d.subsystem == subsystem]
        if verify is not None:
            defs = [d for d in defs if d.verify == verify]
        return defs

    def subsystems(self) -> set[str]:
        out: set[str] = set()
        out.update(d.subsystem for d in self._components.values())
        out.update(d.subsystem for d in self._configs.values())
        out.update(d.subsystem for d in self._analyses.values() if d.subsystem is not None)
        return out

    def clear(self) -> None:
        self._components.clear()
        self._configs.clear()
        self._analyses.clear()


default_registry = UnifiedRegistry()
