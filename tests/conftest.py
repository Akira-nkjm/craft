"""共通 fixture。

framework tests (`tests/craft/`, `tests/integration/`) は `tests/fixtures/systems/`
のスナップショットを tmp に展開して使う。これにより実際の `systems/<name>/data.toml`
を user が編集してもテストには影響しない。

`tests/systems/` は user が書く per-system 解析テスト用で、実 `systems/` を読む。
"""

import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

FIXTURES_SYSTEMS_DIR = Path(__file__).resolve().parent / "fixtures" / "systems"


@pytest.fixture(autouse=True)
def isolated_systems_root(request, tmp_path, monkeypatch):
    """各テストごとに fixtures/systems を tmp に展開し REPO_ROOT を切り替える。

    `tests/systems/` 配下のテストは対象外（実 systems/ を使う）。
    """
    if "/tests/systems/" in str(request.fspath):
        yield None
        return

    fake_root = tmp_path / "craft_root"
    fake_root.mkdir()
    shutil.copytree(FIXTURES_SYSTEMS_DIR, fake_root / "systems")

    import craft.core.paths
    from craft.core.discovery import discover_systems
    from craft.schema.registry import default_registry

    # core.pipeline.merge は __init__.py の `from .merge import merge` で
    # 関数 `merge` に shadow されるため sys.modules 経由で取り直す。
    merge_module = sys.modules["craft.core.pipeline.merge"]

    monkeypatch.setattr(craft.core.paths, "REPO_ROOT", fake_root)
    monkeypatch.setattr(merge_module, "REPO_ROOT", fake_root)
    # NOTE: craft.core.persistence.history.REPO_ROOT は patch しない。
    # git history は systems/*/data.toml の現在内容ではなく commit に依存するため、
    # 実 repo に対して動かす方が正しい。

    snapshot: dict[str, Any] = {
        "components": dict(default_registry._components),
        "configs": dict(default_registry._configs),
        "analyses": dict(default_registry._analyses),
    }
    default_registry.clear()
    discover_systems(root=fake_root / "systems")

    try:
        yield fake_root
    finally:
        default_registry.clear()
        default_registry._components.update(snapshot["components"])
        default_registry._configs.update(snapshot["configs"])
        default_registry._analyses.update(snapshot["analyses"])


@pytest.fixture
def mission_data_backup(isolated_systems_root):
    """isolated tmp の `mission/data.toml` への path。

    各テストごとに fresh copy なので明示的な backup/restore は不要。
    """
    return isolated_systems_root / "systems" / "mission" / "data.toml"


@pytest.fixture
def power_data_backup(isolated_systems_root):
    """isolated tmp の `power/data.toml` への path。"""
    return isolated_systems_root / "systems" / "power" / "data.toml"


@pytest.fixture
def clean_generated_dir(tmp_path, monkeypatch):
    """`generated/` をテスト用 tmp に差し替える。"""
    from craft.api.routers import merge as merge_router
    from craft.api.routers import verify as verify_router
    from craft.core import paths as core_paths
    from craft.core.pipeline import verify as core_verify

    core_merge_mod = sys.modules["craft.core.pipeline.merge"]

    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    new_toml = gen_dir / "merged.toml"
    new_lock = gen_dir / "merged.lock"
    monkeypatch.setattr(core_paths, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(core_paths, "MERGED_TOML", new_toml)
    monkeypatch.setattr(core_paths, "MERGED_LOCK", new_lock)
    monkeypatch.setattr(core_merge_mod, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(core_merge_mod, "MERGED_TOML", new_toml)
    monkeypatch.setattr(core_merge_mod, "MERGED_LOCK", new_lock)
    monkeypatch.setattr(merge_router, "MERGED_TOML", new_toml)
    monkeypatch.setattr(verify_router, "MERGED_TOML", new_toml, raising=False)
    monkeypatch.setattr(core_verify, "MERGED_TOML", new_toml)
    yield gen_dir
