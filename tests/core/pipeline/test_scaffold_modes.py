"""scaffold engine: `--format-only` / `--overwrite` モードのテスト。"""

import pytest

import systems.cdh.scope  # noqa: F401
import systems.mission.scope  # noqa: F401
import systems.orbital.scope  # noqa: F401
import systems.power.scope  # noqa: F401
import systems.thermal.scope  # noqa: F401
from core.io.toml_io import read_toml, read_toml_doc, write_toml_atomic
from core.paths import system_data_path
from core.pipeline.scaffold import scaffold_system


def test_scaffold_format_only_does_not_add_fields(power_data_backup):
    """format-only: registry にあって data.toml に欠落している field は補わない。"""
    data = read_toml(power_data_backup)
    # 既存 field を 1 つ消す
    assert "manufacturer" in data["batteries"]["spec"]
    data["batteries"]["spec"].pop("manufacturer")
    write_toml_atomic(power_data_backup, data)

    result, _ = scaffold_system("power", mode="format-only")

    # format-only は欠落 field を補わない
    assert result.added_paths == ()
    # registry に無い field は無いので removed_warnings も空
    assert result.removed_warnings == ()

    after = read_toml(power_data_backup)
    assert "manufacturer" not in after["batteries"]["spec"]


def test_scaffold_format_only_reorders_fields(power_data_backup):
    """format-only: 既存 field の順序を registry の宣言順に並び替える。"""
    # registry の宣言順:
    #   temp_min_c,
    #   temp_max_c,
    #   capacity_wh, nominal_voltage_v, manufacturer
    # 元 data.toml は (capacity_wh, nominal_voltage_v, manufacturer,
    # temp_min_c, temp_max_c) で
    # registry 順とズレている状態。

    # 念のため明示的に逆順にしておく
    doc = read_toml_doc(power_data_backup)
    spec = doc["batteries"]["spec"]
    saved = {k: spec[k] for k in list(spec.keys())}
    for k in list(spec.keys()):
        del spec[k]
    for k in reversed(list(saved.keys())):
        spec[k] = saved[k]
    write_toml_atomic(power_data_backup, doc)

    scaffold_system("power", mode="format-only")

    after = read_toml(power_data_backup)
    keys = list(after["batteries"]["spec"].keys())
    expected = [
        "mass_kg",
        "temp_min_c",
        "temp_max_c",
        "capacity_wh",
        "nominal_voltage_v",
        "manufacturer",
    ]
    assert keys == expected


def test_scaffold_overwrite_resets_values(power_data_backup):
    """overwrite: 既存値を default に戻し、added_paths に記録する。"""
    data = read_toml(power_data_backup)
    data["batteries"]["spec"]["capacity_wh"] = 999.0
    write_toml_atomic(power_data_backup, data)

    result, _ = scaffold_system("power", mode="overwrite")

    after = read_toml(power_data_backup)
    # capacity_wh は default 無し → placeholder 0.0
    assert after["batteries"]["spec"]["capacity_wh"] == pytest.approx(0.0)
    # added_paths に overwrite マーカー付きで含まれる
    assert any("batteries.spec.capacity_wh" in p and "overwrite" in p for p in result.added_paths)


def test_scaffold_overwrite_does_not_affect_unrelated_subsystem(power_data_backup):
    """overwrite: power のスキャフォールド呼び出しは他 system の data.toml を書き換えない。"""
    other_subsystems = ["thermal", "cdh", "mission", "orbital"]
    snapshots: dict[str, bytes] = {}
    for sub in other_subsystems:
        path = system_data_path(sub)
        if path.exists():
            snapshots[sub] = path.read_bytes()

    scaffold_system("power", mode="overwrite")

    for sub, original in snapshots.items():
        path = system_data_path(sub)
        assert path.read_bytes() == original, f"{sub}/data.toml が変更された"


def test_scaffold_format_only_normalizes_float(power_data_backup):
    """format-only: float field に int が入っていたら float に正規化する。"""
    doc = read_toml_doc(power_data_backup)
    # int として書き込む（tomlkit に int を渡せば整数リテラルになる）
    doc["batteries"]["spec"]["capacity_wh"] = 100
    write_toml_atomic(power_data_backup, doc)

    # 念のため: 書いた直後は int として読める
    pre = read_toml(power_data_backup)
    assert isinstance(pre["batteries"]["spec"]["capacity_wh"], int)

    scaffold_system("power", mode="format-only")

    after = read_toml(power_data_backup)
    val = after["batteries"]["spec"]["capacity_wh"]
    assert isinstance(val, float)
    assert val == pytest.approx(100.0)


def test_scaffold_mode_field_in_result(power_data_backup):
    """ScaffoldResult.mode が 3 つのモードを区別する。"""
    res_default, _ = scaffold_system("power", dry_run=True)
    res_format, _ = scaffold_system("power", dry_run=True, mode="format-only")
    res_overwrite, _ = scaffold_system("power", dry_run=True, mode="overwrite")

    assert res_default.mode == "add-missing"
    assert res_format.mode == "format-only"
    assert res_overwrite.mode == "overwrite"
