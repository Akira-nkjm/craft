"""共通 fixture。"""

import pytest

from core.paths import subsystem_data_path


@pytest.fixture
def power_data_backup():
    """テスト中に power/data.toml を変更する場合のバックアップ・復元 fixture。"""
    path = subsystem_data_path("power")
    backup = path.read_bytes()
    yield path
    path.write_bytes(backup)


@pytest.fixture
def clean_generated_dir(tmp_path, monkeypatch):
    """`generated/` をテスト用 tmp に差し替える。"""
    import sys

    from api.routers import merge as merge_router
    from api.routers import verify as verify_router

    # core/__init__.py が `from core.merge import merge` で関数名と
    # サブモジュール名がぶつかるため、sys.modules 経由でモジュールを取得する。
    core_merge_mod = sys.modules["core.merge"]

    gen_dir = tmp_path / "generated"
    gen_dir.mkdir()
    new_toml = gen_dir / "merged.toml"
    new_lock = gen_dir / "merged.lock"
    monkeypatch.setattr(core_merge_mod, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(core_merge_mod, "MERGED_TOML", new_toml)
    monkeypatch.setattr(core_merge_mod, "MERGED_LOCK", new_lock)
    monkeypatch.setattr(merge_router, "MERGED_TOML", new_toml)
    monkeypatch.setattr(verify_router, "MERGED_TOML", new_toml, raising=False)
    yield gen_dir
