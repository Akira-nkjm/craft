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

import contextlib
import hashlib
import importlib
import importlib.util
import sys
import types
from pathlib import Path
from types import ModuleType
from typing import Any

from craft.core.paths import subsystems_root

# フェーズ順は固定（cross-system 参照の安全のため）
_FILE_ORDER = ("components", "configs", "analyses", "scope")
_UNSET = object()
_scope_modules: dict[str, ModuleType] = {}


def discover_systems(root: Any = _UNSET) -> list[str]:
    """`systems/<name>/` を走査して全 Python ファイルを import。

    全 system の `components` をまず import、続いて `configs`、`analyses`、`scope`
    の順に system 横断でフェーズ並列処理する。

    `root` が importable な `systems` package と別の場所を指す場合は file-only mode
    で import する。file-only mode は `systems.<name>.*` と衝突しない一意な module 名
    を使うため、テスト fixture と実 `systems/` package が sys.modules 上で共存できる。

    Returns:
        発見・import された system 名のリスト。
    """
    if root is _UNSET:
        root = subsystems_root()
    if root is None:
        root = subsystems_root()
    root = Path(root)
    if not root.exists():
        return []

    sub_dirs: list[Path] = []
    for sub_dir in sorted(root.iterdir()):
        if not sub_dir.is_dir():
            continue
        if sub_dir.name.startswith("_") or sub_dir.name.startswith("."):
            continue
        sub_dirs.append(sub_dir)

    file_only = _should_use_file_only(root)
    prefix: str | None = None

    if file_only:
        prefix = _fixture_prefix(root)
        _ensure_package(prefix, root.parent)
        _ensure_package(f"{prefix}.systems", root)
        for sub_dir in sub_dirs:
            _ensure_package(f"{prefix}.systems.{sub_dir.name}", sub_dir)
    else:
        # __init__.py / package を先に import（package mode の場合）
        for sub_dir in sub_dirs:
            _import_subsystem_package(sub_dir)

    # フェーズ並列: 全 system の同じファイルを順番に import
    for file_stem in _FILE_ORDER:
        for sub_dir in sub_dirs:
            module = _import_subsystem_file(sub_dir, file_stem, prefix if file_only else None)
            if module is not None and file_stem == "scope":
                _scope_modules[sub_dir.name] = module

    return [sd.name for sd in sub_dirs]


def get_scope(system: str) -> Any | None:
    """discovery 済み scope object を返す。未発見なら通常 package import に fallback。"""
    module = _scope_modules.get(system)
    if module is None:
        with contextlib.suppress(ModuleNotFoundError):
            module = importlib.import_module(f"systems.{system}.scope")
    if module is None:
        return None
    return getattr(module, system, None)


def _should_use_file_only(root: Path) -> bool:
    """REPO_ROOT patch 等で `systems` package と異なる root を読む場合は file-only。"""
    with contextlib.suppress(ModuleNotFoundError):
        systems_pkg = importlib.import_module("systems")
        paths = [Path(p).resolve() for p in getattr(systems_pkg, "__path__", ())]
        return root.resolve() not in paths
    return False


def _fixture_prefix(root: Path) -> str:
    digest = hashlib.sha1(str(root.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"_craft_fixture_{digest}"


def _ensure_package(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__package__ = name
        sys.modules[name] = module
    module.__path__ = [str(path)]  # type: ignore[attr-defined]


def _import_subsystem_package(sub_dir: Path) -> None:
    """`systems.<name>` package を import（あれば）。

    package が見つからない場合は silent skip（discover_systems 側で file-based
    fallback に切り替える前提）。内部の依存モジュールが見つからない場合や他の
    例外は raise する（実バグの隠蔽防止）。
    """
    sub_name = sub_dir.name
    pkg_name = f"systems.{sub_name}"
    try:
        importlib.import_module(pkg_name)
    except ModuleNotFoundError as e:
        if e.name != pkg_name:
            msg = (
                f"Failed to import system '{sub_name}' package '{pkg_name}': "
                f"missing module '{e.name}'"
            )
            raise ModuleNotFoundError(msg) from e
    except Exception as e:
        msg = f"Failed to import system '{sub_name}' package '{pkg_name}'"
        raise ImportError(msg) from e


def _import_subsystem_file(sub_dir: Path, file_stem: str, prefix: str | None) -> ModuleType | None:
    """1 system の 1 ファイルを import。package mode → fallback file mode。

    file 自体が見つからない場合は silent skip（その system にそのフェーズが
    無いだけ）。内部の依存モジュールが見つからない場合や他の例外は raise する。
    """
    sub_name = sub_dir.name
    pkg_name = f"{prefix}.systems.{sub_name}" if prefix else f"systems.{sub_name}"
    mod_full = f"{pkg_name}.{file_stem}"
    cached = sys.modules.get(mod_full)
    if cached is not None:
        return cached

    if prefix is None:
        # package として import 可能なら通常 import
        try:
            return importlib.import_module(mod_full)
        except ModuleNotFoundError as e:
            if e.name != mod_full:
                _raise_module_not_found(sub_name, file_stem, mod_full, e)
            # この file は存在しない → file-based fallback へ
        except Exception as e:
            _raise_import_error(sub_name, file_stem, mod_full, e)

    # fallback: ファイル直接 import
    py_path = sub_dir / f"{file_stem}.py"
    if not py_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(mod_full, py_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_full] = module
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as e:
        sys.modules.pop(mod_full, None)
        _raise_module_not_found(sub_name, file_stem, mod_full, e, py_path)
    except Exception as e:
        sys.modules.pop(mod_full, None)
        _raise_import_error(sub_name, file_stem, mod_full, e, py_path)
    return module


def _raise_module_not_found(
    sub_name: str,
    file_stem: str,
    mod_name: str,
    e: ModuleNotFoundError,
    py_path: Path | None = None,
) -> None:
    path_context = f" from '{py_path}'" if py_path is not None else ""
    msg = (
        f"Failed to import system '{sub_name}' file '{file_stem}' "
        f"as '{mod_name}'{path_context}: missing module '{e.name}'"
    )
    raise ModuleNotFoundError(msg) from e


def _raise_import_error(
    sub_name: str,
    file_stem: str,
    mod_name: str,
    e: Exception,
    py_path: Path | None = None,
) -> None:
    path_context = f" from '{py_path}'" if py_path is not None else ""
    msg = f"Failed to import system '{sub_name}' file '{file_stem}' as '{mod_name}'{path_context}"
    raise ImportError(msg) from e
