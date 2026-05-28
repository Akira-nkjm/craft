"""Subsystem 自動 discovery。

`systems/<name>/` 配下の Python ファイルを import 順に走らせて、
`Component.__init_subclass__` / `Config.__init_subclass__` / `@analysis` を発火させる。
"""

import importlib
import importlib.util
from pathlib import Path

from craft.core.paths import subsystems_root

# import 順は固定（system 跨ぎ参照の安全のため）
_FILE_ORDER = ("components", "configs", "analyses", "scope")


def discover_systems(root: Path | None = None) -> list[str]:
    """`systems/<name>/` を走査して全 Python ファイルを import。

    既に installed package として `systems.<name>.<file>` で import 可能であれば
    通常の `importlib.import_module` を使う。そうでなければ `spec_from_file_location`
    でファイル直接 import。

    Returns:
        発見・import された system 名のリスト。
    """
    if root is None:
        root = subsystems_root()
    if not root.exists():
        return []

    found: list[str] = []
    for sub_dir in sorted(root.iterdir()):
        if not sub_dir.is_dir():
            continue
        if sub_dir.name.startswith("_") or sub_dir.name.startswith("."):
            continue
        _import_subsystem(sub_dir)
        found.append(sub_dir.name)
    return found


def _import_subsystem(sub_dir: Path) -> None:
    """1 system 分の Python ファイルを順に import。"""
    sub_name = sub_dir.name
    # __init__.py 経由で package として import を試みる
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
    else:
        for file_stem in _FILE_ORDER:
            mod = f"{pkg_name}.{file_stem}"
            try:
                importlib.import_module(mod)
            except ModuleNotFoundError as e:
                if e.name == mod:
                    continue
                _raise_module_not_found(sub_name, file_stem, mod, e)
            except Exception as e:
                _raise_import_error(sub_name, file_stem, mod, e)
        return

    # fallback: ファイル直接 import
    for file_stem in _FILE_ORDER:
        py_path = sub_dir / f"{file_stem}.py"
        if not py_path.exists():
            continue
        mod_name = f"systems.{sub_name}.{file_stem}"
        spec = importlib.util.spec_from_file_location(mod_name, py_path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except ModuleNotFoundError as e:
            _raise_module_not_found(sub_name, file_stem, mod_name, e, py_path)
        except Exception as e:
            _raise_import_error(sub_name, file_stem, mod_name, e, py_path)


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
    msg = (
        f"Failed to import system '{sub_name}' file '{file_stem}' "
        f"as '{mod_name}'{path_context}"
    )
    raise ImportError(msg) from e
