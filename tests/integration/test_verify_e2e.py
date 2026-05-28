"""End-to-end: merge → veriq verify が結果を返すか。"""

import veriq as vq

from craft.core.discovery import get_scope
from craft.core.pipeline.merge import MERGED_TOML, merge


def test_evaluate_project_runs_and_reports_verifications(clean_generated_dir):
    project = vq.Project("Craft")
    for name in ("power", "orbital", "mission"):
        scope = get_scope(name)
        assert scope is not None
        project.add_scope(scope)
    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)

    assert result.success is True

    tree = result.get_scope_tree("power")
    assert tree is not None
    verif_by_name = {str(node.path).split("?")[-1]: node.value for node in tree.verifications}
    assert "verify_battery_capacity" in verif_by_name
    # shared_spec=True: 全 battery が capacity_wh=100、要求 50 → 100*0.8=80 >= 50 → True
    assert verif_by_name["verify_battery_capacity"] is True

    calc_by_name = {str(node.path).split("@")[-1]: node.value for node in tree.calculations}
    assert calc_by_name["total_pdm_power_w"] == 8.0
