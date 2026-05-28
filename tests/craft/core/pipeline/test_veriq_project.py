"""Unit tests for core.veriq_project.build_project."""

from unittest.mock import MagicMock, patch

from craft.core.pipeline.veriq_project import build_project


def test_build_project_adds_scope_for_each_system():
    registry = MagicMock()
    registry.systems.return_value = {"alpha", "beta"}

    mock_alpha_scope = MagicMock()
    mock_beta_scope = MagicMock()
    mock_project = MagicMock()

    scopes = {"alpha": mock_alpha_scope, "beta": mock_beta_scope}

    with (
        patch("craft.core.pipeline.veriq_project.get_scope", side_effect=scopes.get),
        patch("craft.core.pipeline.veriq_project.vq.Project", return_value=mock_project),
    ):
        result = build_project(registry)

    assert result is mock_project
    assert mock_project.add_scope.call_count == 2
    added = {call.args[0] for call in mock_project.add_scope.call_args_list}
    assert mock_alpha_scope in added
    assert mock_beta_scope in added


def test_build_project_skips_system_without_scope_attribute():
    registry = MagicMock()
    registry.systems.return_value = {"noscope"}
    mock_project = MagicMock()

    with (
        patch("craft.core.pipeline.veriq_project.get_scope", return_value=None),
        patch("craft.core.pipeline.veriq_project.vq.Project", return_value=mock_project),
    ):
        build_project(registry)

    mock_project.add_scope.assert_not_called()


def test_build_project_iterates_systems_in_sorted_order():
    registry = MagicMock()
    registry.systems.return_value = {"zeta", "alpha", "mu"}

    call_order: list[str] = []

    def _fake_get_scope(sys_name: str):
        call_order.append(sys_name)
        return MagicMock()

    with (
        patch("craft.core.pipeline.veriq_project.get_scope", side_effect=_fake_get_scope),
        patch("craft.core.pipeline.veriq_project.vq.Project", return_value=MagicMock()),
    ):
        build_project(registry)

    assert call_order == sorted(call_order)


def test_build_project_names_project_craft():
    registry = MagicMock()
    registry.systems.return_value = set()

    with patch("craft.core.pipeline.veriq_project.vq.Project") as mock_proj_cls:
        mock_proj_cls.return_value = MagicMock()
        build_project(registry)

    mock_proj_cls.assert_called_once_with("Craft")
