"""共通 fixture。"""

import pytest

from core.paths import system_data_path


@pytest.fixture
def mission_data_backup():
    """テスト中に mission/data.toml を変更する場合のバックアップ・復元 fixture。"""
    path = system_data_path("mission")
    backup = path.read_bytes()
    yield path
    path.write_bytes(backup)


@pytest.fixture
def power_data_backup():
    """テスト中に power/data.toml を変更する場合のバックアップ・復元 fixture。"""
    path = system_data_path("power")
    backup = path.read_bytes()
    yield path
    path.write_bytes(backup)


@pytest.fixture
def clean_generated_dir(tmp_path, monkeypatch):
    """`generated/` をテスト用 tmp に差し替える。"""
    import sys

    from api.routers import merge as merge_router
    from api.routers import verify as verify_router
    from core import paths as core_paths
    from core import verify as core_verify

    # core.merge re-exports these for backward compat, but the source of truth is core.paths.
    core_merge_mod = sys.modules["core.merge"]

    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    new_toml = gen_dir / "merged.toml"
    new_lock = gen_dir / "merged.lock"
    # Primary patch: the source of truth in core.paths.
    monkeypatch.setattr(core_paths, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(core_paths, "MERGED_TOML", new_toml)
    monkeypatch.setattr(core_paths, "MERGED_LOCK", new_lock)
    # Re-exported names in core.merge (callers that imported earlier still see old refs).
    monkeypatch.setattr(core_merge_mod, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(core_merge_mod, "MERGED_TOML", new_toml)
    monkeypatch.setattr(core_merge_mod, "MERGED_LOCK", new_lock)
    monkeypatch.setattr(merge_router, "MERGED_TOML", new_toml)
    monkeypatch.setattr(verify_router, "MERGED_TOML", new_toml, raising=False)
    monkeypatch.setattr(core_verify, "MERGED_TOML", new_toml)
    yield gen_dir
