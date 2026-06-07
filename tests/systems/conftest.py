"""`tests/systems/` 用 conftest。

`tests/systems/` のテストは **実 `systems/`** を読む（top-level conftest の
`isolated_systems_root` fixture は `/tests/systems/` パスを除外する）。しかし同一
pytest プロセス内で先に走る framework テスト（`tests/craft` / `tests/integration`）
の `isolated_systems_root` fixture が、fixture systems を discover して global な
registry / veriq scope / root-model 解決を汚染する。その結果、実 systems を前提に
する `tests/systems/` のテストが汚染状態を引き継いでしまう。

そこで各テスト前に **実 systems を完全に reload** して registry と scope を実データ
側へ戻す。reload はモジュールキャッシュを使わず `@register` / `_build_and_attach`
を確実に再実行するため、汚染後でも一貫した実 state を復元できる。
"""

import contextlib
import importlib
import sys
from pathlib import Path

import pytest

from craft.core.discovery import _scope_modules, subsystems_root
from craft.schema import default_registry

_FILE_ORDER = ("components", "configs", "analyses", "scope")


def _real_system_names() -> list[str]:
    root = Path(subsystems_root())
    return sorted(
        d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))
    )


def _reload_real_systems() -> None:
    """registry を clear し、実 systems の全モジュールを依存順に reload する。"""
    default_registry.clear()
    names = _real_system_names()
    for stem in _FILE_ORDER:
        for name in names:
            mod_name = f"systems.{name}.{stem}"
            cached = sys.modules.get(mod_name)
            if cached is not None:
                importlib.reload(cached)
            else:
                # その system に当該フェーズが無いだけ → skip。
                with contextlib.suppress(ModuleNotFoundError):
                    importlib.import_module(mod_name)
    # discovery が参照する scope module キャッシュも実データ側へ揃える。
    for name in names:
        scope_mod = sys.modules.get(f"systems.{name}.scope")
        if scope_mod is not None:
            _scope_modules[name] = scope_mod


@pytest.fixture(autouse=True)
def real_systems_restored():
    """各テスト前に実 systems を reload して global state を実データへ戻す。"""
    _reload_real_systems()
    yield
