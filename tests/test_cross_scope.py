"""Cross-scope vq.Ref（imports=["orbital"]）の動作確認。

Power scope の `required_orbit_energy_wh` は同 scope の `@total_pdm_power_w` と
orbital scope の `$.orbitalparams.eclipse_duration_s` を参照する。
"""

import pytest
import veriq as vq
from fastapi.testclient import TestClient

from api.main import app
from core.discovery import discover_systems
from core.merge import MERGED_TOML, merge
from schema import default_registry


def _ensure_discovered() -> None:
    discover_systems()


def test_orbital_subsystem_registered():
    _ensure_discovered()
    assert "orbital" in default_registry.systems()


def test_orbital_config_registered():
    _ensure_discovered()
    names = {c.name for c in default_registry.configs(system="orbital")}
    assert "orbitalparams" in names


def test_required_orbit_energy_analysis_registered():
    _ensure_discovered()
    adef = default_registry.analysis_or_none("power", "required_orbit_energy_wh")
    assert adef is not None
    assert adef.imports == ("orbital",)
    assert adef.verify is False


def test_cross_scope_evaluate(clean_generated_dir):
    _ensure_discovered()
    from systems.orbital.scope import orbital
    from systems.power.scope import power

    project = vq.Project("Craft")
    project.add_scope(power)
    project.add_scope(orbital)

    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)

    assert result.success is True, f"errors: {result.errors}"

    tree = result.get_scope_tree("power")
    assert tree is not None
    calc_by_name = {str(node.path).split("@")[-1]: node.value for node in tree.calculations}
    assert "required_orbit_energy_wh" in calc_by_name
    # 8.0 W * 2100 s / 3600 = 4.6667 Wh
    assert calc_by_name["required_orbit_energy_wh"] == pytest.approx(8.0 * 2100.0 / 3600.0)


def test_required_orbit_energy_via_api(clean_generated_dir):
    with TestClient(app) as c:
        r = c.post("/analyses/power/required_orbit_energy_wh", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["analysis"] == "required_orbit_energy_wh"
    assert body["system"] == "power"
    assert body["verify"] is False
    assert body["value"] == pytest.approx(8.0 * 2100.0 / 3600.0)
