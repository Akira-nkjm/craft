"""merge engine のテスト。"""

import sys

import systems.power.scope  # noqa: F401
from core.io.toml_io import read_toml
from core.merge import is_merge_stale, merge


def _merge_mod():
    """`core.merge` モジュール本体（`core/__init__.py` の関数 re-export と区別）。"""
    return sys.modules["core.merge"]


def test_merge_dry_run_does_not_write(clean_generated_dir):
    mod = _merge_mod()
    result, merged = merge(dry_run=True)
    assert result.written is False
    assert not mod.MERGED_TOML.exists()
    assert "power" in merged


def test_merge_writes_file_and_lock(clean_generated_dir):
    mod = _merge_mod()
    result, _ = merge()
    assert result.written is True
    assert mod.MERGED_TOML.exists()
    assert mod.MERGED_LOCK.exists()

    lock = read_toml(mod.MERGED_LOCK)
    assert "systems/power/data.toml" in lock["sources"]


def test_merge_subsystems_filter(clean_generated_dir):
    result, merged = merge(systems=["power"])
    assert result.systems == ("power",)
    assert set(merged.keys()) == {"power"}


def test_is_merge_stale_after_data_change(clean_generated_dir, power_data_backup):
    merge()
    assert is_merge_stale() is False

    # 元 data.toml を書き換える
    power_data_backup.write_bytes(power_data_backup.read_bytes() + b"\n# touched\n")
    assert is_merge_stale() is True
