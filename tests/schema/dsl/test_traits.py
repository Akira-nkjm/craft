"""_Trait protocol のテスト。"""

import systems.aocs.scope  # noqa: F401 — trigger aocs system registration
import systems.power.scope  # noqa: F401 — trigger power system registration
import systems.thermal.scope  # noqa: F401 — trigger thermal system registration
from schema import default_registry
from schema.dsl.traits import (
    MultiInstance,
    Placeable,
    PowerConsuming,
    SpecOnly,
    _Trait,
)


def test_trait_base_has_cardinality():
    assert _Trait.cardinality == "single"


def test_trait_base_has_design_extra():
    assert _Trait.design_extra == {}


def test_trait_base_has_spec_only():
    assert _Trait.spec_only is False


def test_multi_instance_cardinality():
    assert MultiInstance.cardinality == "multi"


def test_power_consuming_design_extra():
    assert "power_modes" in PowerConsuming.design_extra


def test_spec_only_flag():
    assert SpecOnly.spec_only is True


def test_placeable_design_extra():
    assert "placement" in Placeable.design_extra


def test_component_without_placeable_has_no_placement():
    # PanelSurface は SpecOnly のみ（Placeable なし）

    panel = default_registry.component("thermal", "panelsurface")
    assert panel.design is None  # SpecOnly → design なし


def test_component_with_placeable_has_placement():
    battery = default_registry.component("power", "battery")
    assert battery.design is not None
    assert "placement" in battery.design.model_fields


def test_component_without_placeable_no_placement_field():
    from schema import Component, fld

    # Use a unique system name to avoid leaking into other tests'
    # default_registry.components(system="power") assertions.
    class TestNoPlaceable(Component, system="_trait_test"):
        value: float = fld(default=0.0)

    assert TestNoPlaceable.Design is not None  # pyrefly: ignore[missing-attribute]
    assert "placement" not in TestNoPlaceable.Design.model_fields  # pyrefly: ignore[missing-attribute]


def test_battery_is_multi_instance_with_placeable():
    battery = default_registry.component("power", "battery")
    assert battery.cardinality == "multi"
    assert "Placeable" in battery.traits
    assert "MultiInstance" in battery.traits
