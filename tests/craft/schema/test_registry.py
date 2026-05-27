"""Registry auto-registration の確認。"""

import systems.power.scope  # noqa: F401 — トリガ
from craft.schema import default_registry


def test_power_subsystem_registered():
    assert "power" in default_registry.systems()


def test_components_registered():
    names = {c.name for c in default_registry.components(system="power")}
    assert names == {"battery", "solarpanel", "pdm"}


def test_battery_models_built():
    battery = default_registry.component("power", "battery")
    assert "capacity_wh" in battery.spec.model_fields
    assert "temp_min_c" in battery.spec.model_fields  # trait 経由
    assert battery.design is not None
    assert "depth_of_discharge" in battery.design.model_fields
    assert battery.requirements is not None
    assert "depth_of_discharge_max" in battery.requirements.model_fields


def test_pdm_has_power_consuming_fields():
    pdm = default_registry.component("power", "pdm")
    # PowerConsuming trait 由来
    assert "power_per_unit_w" in pdm.spec.model_fields
    assert pdm.design is not None
    assert "power_modes" in pdm.design.model_fields


def test_battery_is_multi_instance():
    battery = default_registry.component("power", "battery")
    assert battery.cardinality == "multi"
    assert "MultiInstance" in battery.traits


def test_analyses_registered():
    analyses = default_registry.analyses(system="power")
    names = {a.name for a in analyses}
    assert names == {
        "total_pdm_power_w",
        "pdm_power_per_mode_w",
        "verify_battery_capacity",
        "required_orbit_energy_wh",
    }

    verify = default_registry.analysis("power", "verify_battery_capacity")
    assert verify.verify is True
    calc = default_registry.analysis("power", "total_pdm_power_w")
    assert calc.verify is False
