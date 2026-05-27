"""Scaffold engine — registry → data.toml 雛形（add-missing）。

仕様: plan/Craft/01_仕様/データパイプライン.md §4

実装:
- `tomlkit` 経由でコメントを保持
- 既存値は default で `--preserve-values`（破壊しない）
- `--format-only`: 既存値は触らず順序・コメントだけ整形
- `--overwrite`: 既存値も default に戻す（破壊的、確認は呼び元が責任）
- shared_spec=True (MultiInstance) → `<plural>.spec` 直下に spec を置く

パッケージ構造:
- `builders.py`: component / config 単位の雛形ロジック
- `formatting.py`: 出力テキストの空行・タイトル正規化
- `tomlkit_helpers.py`: tomlkit 構造操作ヘルパー
"""

from dataclasses import dataclass, field
from pathlib import Path

import tomlkit
from tomlkit import TOMLDocument

from core.io.toml_io import read_toml_doc, write_toml_atomic
from core.paths import system_data_path
from core.pipeline.scaffold.builders import (
    ScaffoldMode,
    scaffold_component,
    scaffold_config,
)
from core.pipeline.scaffold.formatting import normalize_scaffold_spacing
from schema import default_registry

__all__ = [
    "ScaffoldMode",
    "ScaffoldResult",
    "scaffold_all",
    "scaffold_system",
]


@dataclass(frozen=True, slots=True)
class ScaffoldResult:
    system: str
    file_path: Path
    written: bool
    added_paths: tuple[str, ...] = ()
    removed_warnings: tuple[str, ...] = field(default_factory=tuple)
    mode: str = "add-missing"


def scaffold_system(
    system: str,
    *,
    dry_run: bool = False,
    mode: ScaffoldMode = "add-missing",
) -> tuple[ScaffoldResult, TOMLDocument]:
    """1 つの system の data.toml を雛形と diff merge する。

    Args:
        mode: "add-missing" (default) / "format-only" / "overwrite"

    Returns:
        (result, updated TOMLDocument)
    """
    components = default_registry.components(system=system)
    configs = default_registry.configs(system=system)
    if not components and not configs:
        raise ValueError(f"No components/configs registered for system '{system}'")

    data_path = system_data_path(system)
    doc = read_toml_doc(data_path)

    added: list[str] = []
    removed: list[str] = []

    for cdef in components:
        scaffold_component(doc, cdef, added, removed, mode=mode)
    for cfg in configs:
        scaffold_config(doc, cfg, added, removed, mode=mode)

    result = ScaffoldResult(
        system=system,
        file_path=data_path,
        written=not dry_run,
        added_paths=tuple(added),
        removed_warnings=tuple(removed),
        mode=mode,
    )

    if not dry_run:
        content = normalize_scaffold_spacing(tomlkit.dumps(doc))
        write_toml_atomic(data_path, content)

    return result, doc


def scaffold_all(
    *,
    dry_run: bool = False,
    mode: ScaffoldMode = "add-missing",
) -> list[ScaffoldResult]:
    out: list[ScaffoldResult] = []
    for sub in sorted(default_registry.systems()):
        result, _ = scaffold_system(sub, dry_run=dry_run, mode=mode)
        out.append(result)
    return out
