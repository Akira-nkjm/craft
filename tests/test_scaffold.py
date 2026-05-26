"""scaffold engine のテスト。"""

import systems.power.scope  # noqa: F401
from core.scaffold import scaffold_system
from core.toml_io import read_toml, write_toml_atomic


def test_scaffold_existing_data_is_noop(power_data_backup):
    """既存 data.toml が完全なら added は空。"""
    result, _ = scaffold_system("power", dry_run=True)
    assert result.added_paths == ()
    assert result.removed_warnings == ()


def test_scaffold_adds_missing_field(power_data_backup):
    """欠落した required field を 0.0 placeholder で追加。"""
    data = read_toml(power_data_backup)
    data["batteries"]["aux"]["design"] = {}
    write_toml_atomic(power_data_backup, data)

    result, _ = scaffold_system("power", dry_run=True)
    assert "batteries.aux.design.depth_of_discharge" in result.added_paths


def test_scaffold_preserves_existing_values(power_data_backup):
    """既存値は絶対に変更しない（shared_spec の値）。"""
    scaffold_system("power")
    data = read_toml(power_data_backup)
    # shared_spec=True: batteries.spec.capacity_wh が共有
    assert data["batteries"]["spec"]["capacity_wh"] == 100.0


def test_scaffold_unknown_subsystem_raises():
    import pytest

    with pytest.raises(ValueError):
        scaffold_system("nonexistent")


def test_scaffold_warns_unknown_field(power_data_backup):
    """registry に無い field は警告対象（削除はされない）。"""
    data = read_toml(power_data_backup)
    data["batteries"]["spec"]["typo_field"] = 999
    write_toml_atomic(power_data_backup, data)

    result, after = scaffold_system("power", dry_run=True)
    assert any("typo_field" in w for w in result.removed_warnings)
    # 削除されていない
    assert after["batteries"]["spec"]["typo_field"] == 999
