"""scaffold engine のテスト。"""

import systems.power.scope  # noqa: F401
from core.io.toml_io import read_toml, write_toml_atomic
from core.scaffold import scaffold_system


def test_scaffold_existing_data_is_noop(power_data_backup):
    """scaffold は冪等：2回目の実行では added は空。"""
    scaffold_system("power")
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


def test_scaffold_key_source_adds_missing_mode(mission_data_backup):
    """power_modes に key_source の不足モードが自動補完される。"""
    import tomlkit

    import systems.mission.scope  # noqa: F401
    from core.io.toml_io import write_toml_atomic

    # mission に新モードを追加
    mission_doc = tomlkit.parse(mission_data_backup.read_text())
    new_mode = tomlkit.table()
    new_mode["description"] = "テスト用モード"
    new_mode["max_duration_s"] = 0.0
    new_mode["is_initial_mode"] = False
    new_mode["allowed_transitions"] = []
    mission_doc["operation_mode_configs"]["test_mode"] = new_mode  # type: ignore[index]
    write_toml_atomic(mission_data_backup, mission_doc)

    result, _ = scaffold_system("power", dry_run=True)
    assert any("power_modes.test_mode" in p for p in result.added_paths)


def test_scaffold_key_source_preserves_existing_modes(power_data_backup):
    """既存の power_modes エントリは scaffold で上書きされない。"""
    import systems.mission.scope  # noqa: F401

    _result, after = scaffold_system("power")
    assert after["pdms"]["main"]["design"]["power_modes"]["nominal"] is True


def test_scaffold_warns_unknown_field(power_data_backup):
    """registry に無い field は警告対象（削除はされない）。"""
    data = read_toml(power_data_backup)
    data["batteries"]["spec"]["typo_field"] = 999
    write_toml_atomic(power_data_backup, data)

    result, after = scaffold_system("power", dry_run=True)
    assert any("typo_field" in w for w in result.removed_warnings)
    # 削除されていない
    assert after["batteries"]["spec"]["typo_field"] == 999
