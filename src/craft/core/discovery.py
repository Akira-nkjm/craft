"""Subsystem 自動 discovery。

`systems/<name>/` 配下の Python ファイルを import 順に走らせて、
`Component.__init_subclass__` / `Config.__init_subclass__` / `@analysis` を発火させる。

import 順序はフェーズ並列:
  1. すべての system の `components.py`
  2. すべての system の `configs.py`
  3. すべての system の `analyses.py`
  4. すべての system の `scope.py`

これにより analyses.py から `default_registry.components()` を呼ぶような動的構築
（`craft.analyses.make_aggregate_analysis` など）でも、全 system の component が
登録済みの状態で参照できる。
"""

import importlib
import importlib.util
from pathlib import Path

from craft.core.paths import subsystems_root

# フェーズ順は固定（cross-system 参照の安全のため）
_FILE_ORDER = ("components", "configs", "analyses", "scope")


def discover_systems(root: Path | None = None) -> list[str]:
    """`systems/<name>/` を走査して全 Python ファイルを import。

    全 system の `components` をまず import、続いて `configs`、`analyses`、`scope`
    の順に system 横断でフェーズ並列処理する。

    Returns:
        発見・import された system 名のリスト。
    """
    if root is None:
        root = subsystems_root()
    if not root.exists():
        return []

    sub_dirs: list[Path] = []
    for sub_dir in sorted(root.iterdir()):
        if not sub_dir.is_dir():
            continue
        if sub_dir.name.startswith("_") or sub_dir.name.startswith("."):
            continue
        sub_dirs.append(sub_dir)

    # __init__.py / package を先に import（package mode の場合）
    for sub_dir in sub_dirs:
        _import_subsystem_package(sub_dir)

    # フェーズ並列: 全 system の同じファイルを順番に import
    for file_stem in _FILE_ORDER:
        for sub_dir in sub_dirs:
            _import_subsystem_file(sub_dir, file_stem)

    return [sd.name for sd in sub_dirs]


def _import_subsystem_package(sub_dir: Path) -> None:
    """`systems.<name>` package を import（あれば）。"""
    sub_name = sub_dir.name
    pkg_name = f"systems.{sub_name}"
    try:
        importlib.import_module(pkg_name)
    except ModuleNotFoundError:
        pass


def _import_subsystem_file(sub_dir: Path, file_stem: str) -> None:
    """1 system の 1 ファイルを import。package mode → fallback file mode。"""
    sub_name = sub_dir.name
    pkg_name = f"systems.{sub_name}"
    mod_full = f"{pkg_name}.{file_stem}"

    # package として import 可能なら通常 import
    try:
        importlib.import_module(mod_full)
        return
    except ModuleNotFoundError:
        pass

    # fallback: ファイル直接 import
    py_path = sub_dir / f"{file_stem}.py"
    if not py_path.exists():
        return
    spec = importlib.util.spec_from_file_location(mod_full, py_path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
