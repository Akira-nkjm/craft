"""Root model code generation tests."""

from typing import Any

import veriq as vq

from craft.schema import build_system_root_model


def _tag_names(field: Any) -> set[str]:
    return {tag.name for tag in field.metadata if isinstance(tag, vq.Tag)}


def test_component_fields_are_tagged_with_component_and_traits(isolated_systems_root):
    root_model = build_system_root_model(
        "power",
        isolated_systems_root / "systems" / "power" / "data.toml",
    )

    assert _tag_names(root_model.model_fields["pdms"]) == {
        "Component",
        "MultiInstance",
        "PowerConsuming",
        "Placeable",
    }
    assert _tag_names(root_model.model_fields["batteries"]) == {
        "Component",
        "MultiInstance",
        "TemperatureSensitive",
        "Placeable",
    }


def test_config_fields_are_not_tagged(isolated_systems_root):
    root_model = build_system_root_model(
        "mission",
        isolated_systems_root / "systems" / "mission" / "data.toml",
    )

    assert _tag_names(root_model.model_fields["missionprofile"]) == set()
    assert _tag_names(root_model.model_fields["operation_mode_configs"]) == set()
