"""A2: ネスト Pydantic model を field 型に / A4: Component に subsystem= 明示。

ネスト型: `subsystems/cdh/components.py` の OBC に `bus_interface: BusInterface = fld(...)`
を追加した。data.toml の `[obc.spec.bus_interface]` から正しく型付きで取れることを確認する。

A4: `Component.__init_subclass__` の `subsystem="..."` キーワード明示が
ファイル位置とは独立に効くこと（registry に明示 subsystem で登録される）を確認する。
ただし default_registry は他テストと共有なので、テスト内クラスは
適当な名前にして重複登録を避ける。
"""

import pytest
from pydantic import ValidationError

import subsystems.cdh.scope  # noqa: F401 — discovery

# ─── A2: nested model ───────────────────────────────────────────────


def test_obc_bus_interface_is_nested_pydantic_model():
    from subsystems.cdh.components import OBC, BusInterface

    bus_field = OBC.Spec.model_fields["bus_interface"]
    # annotation が BusInterface サブクラス（または同型）
    assert bus_field.annotation is BusInterface


def test_obc_bus_interface_loads_from_toml():
    """data.toml の `[obc.spec.bus_interface]` がネスト model に validate される。"""
    from core.paths import subsystem_data_path
    from core.toml_io import read_toml
    from subsystems.cdh.components import OBC

    data = read_toml(subsystem_data_path("cdh"))
    spec = OBC.Spec.model_validate(data["obc"]["spec"])
    assert spec.bus_interface.voltage_v == 28.0
    assert spec.bus_interface.rated_current_a == 2.5
    assert spec.bus_interface.protocol == "CAN"


def test_obc_bus_interface_validation_error_on_missing():
    """ネスト model 内の required field が無いと ValidationError。"""
    from subsystems.cdh.components import OBC

    with pytest.raises(ValidationError):
        OBC.Spec.model_validate(
            {
                "clock_mhz": 100,
                "ram_mb": 512,
                "storage_gb": 32.0,
                "architecture": "X",
                "default_power_consumption_per_unit_w": 3.5,
                "operating_temperature_min_c": -40.0,
                "operating_temperature_max_c": 85.0,
                "bus_interface": {"voltage_v": 28.0},  # rated_current_a 欠落
            }
        )


# ─── A4: explicit subsystem keyword ─────────────────────────────────


def test_explicit_subsystem_keyword_registers_under_given_name():
    """ファイルパスから推論されない subsystem で登録できる。"""
    from schema import Component, default_registry, fld

    # 一意な名前にして既存テストを汚染しない
    class A4ExampleProbe(Component, subsystem="_a4_test"):
        value: float = fld(ge=0)

    defn = default_registry.component("_a4_test", "a4exampleprobe")
    assert defn.subsystem == "_a4_test"
    assert defn.name == "a4exampleprobe"
    # cleanup
    default_registry._components.pop(("_a4_test", "a4exampleprobe"), None)


def test_explicit_plural_keyword():
    """`plural=` を明示できる。"""
    from schema import Component, MultiInstance, default_registry, fld

    class A4PluralProbe(Component, MultiInstance, subsystem="_a4_test", plural="probes"):
        rating: float = fld(ge=0)

    defn = default_registry.component("_a4_test", "a4pluralprobe")
    assert defn.plural == "probes"
    default_registry._components.pop(("_a4_test", "a4pluralprobe"), None)
