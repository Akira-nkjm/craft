"""Unit tests for core.veriq_project.build_project."""

from unittest.mock import MagicMock, patch

from core.veriq_project import build_project


def _make_fake_importlib(system_to_scope: dict) -> MagicMock:
    """Return a mock importlib whose import_module returns scope mocks by system name."""
    mock_importlib = MagicMock()

    def _fake_import(name: str):
        # name is "systems.<sys>.scope"
        parts = name.split(".")
        if len(parts) == 3 and parts[0] == "systems" and parts[2] == "scope":
            sys_name = parts[1]
            mod = MagicMock()
            if sys_name in system_to_scope:
                setattr(mod, sys_name, system_to_scope[sys_name])
            else:
                # no attribute → build_project should skip it
                del mod.__dict__[sys_name]  # ensure getattr returns the MagicMock auto-attr
            return mod
        raise ImportError(f"Unexpected import: {name!r}")

    mock_importlib.import_module.side_effect = _fake_import
    return mock_importlib


def test_build_project_adds_scope_for_each_system():
    registry = MagicMock()
    registry.systems.return_value = {"alpha", "beta"}

    mock_alpha_scope = MagicMock()
    mock_beta_scope = MagicMock()
    mock_project = MagicMock()

    mock_importlib = MagicMock()

    def _fake_import(name: str):
        if name == "systems.alpha.scope":
            mod = MagicMock()
            mod.alpha = mock_alpha_scope
            return mod
        if name == "systems.beta.scope":
            mod = MagicMock()
            mod.beta = mock_beta_scope
            return mod
        raise ImportError(f"No module named {name!r}")

    mock_importlib.import_module.side_effect = _fake_import

    with (
        patch("core.veriq_project.importlib", mock_importlib),
        patch("core.veriq_project.vq.Project", return_value=mock_project),
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

    mock_importlib = MagicMock()

    def _fake_import(name: str):
        if name == "systems.noscope.scope":
            mod = MagicMock(spec=[])  # no 'noscope' attribute
            return mod
        raise ImportError(f"No module named {name!r}")

    mock_importlib.import_module.side_effect = _fake_import
    mock_project = MagicMock()

    with (
        patch("core.veriq_project.importlib", mock_importlib),
        patch("core.veriq_project.vq.Project", return_value=mock_project),
    ):
        build_project(registry)

    mock_project.add_scope.assert_not_called()


def test_build_project_iterates_systems_in_sorted_order():
    registry = MagicMock()
    registry.systems.return_value = {"zeta", "alpha", "mu"}

    call_order: list[str] = []
    mock_importlib = MagicMock()

    def _fake_import(name: str):
        sys_name = name.split(".")[1]
        call_order.append(sys_name)
        mod = MagicMock()
        setattr(mod, sys_name, MagicMock())
        return mod

    mock_importlib.import_module.side_effect = _fake_import

    with (
        patch("core.veriq_project.importlib", mock_importlib),
        patch("core.veriq_project.vq.Project", return_value=MagicMock()),
    ):
        build_project(registry)

    assert call_order == sorted(call_order)


def test_build_project_names_project_craft():
    registry = MagicMock()
    registry.systems.return_value = set()

    with patch("core.veriq_project.vq.Project") as mock_proj_cls:
        mock_proj_cls.return_value = MagicMock()
        build_project(registry)

    mock_proj_cls.assert_called_once_with("Craft")
