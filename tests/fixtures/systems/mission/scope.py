"""Mission fixture veriq scope."""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry

from . import configs as _configs  # noqa: F401

mission = vq.Scope("mission")


def _build_and_attach() -> type:
    root_model = build_system_root_model("mission", system_data_path("mission"))
    mission.root_model()(root_model)
    for adef in default_registry.analyses(system="mission"):
        if adef.verify:
            mission.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            mission.calculation(adef.name, imports=adef.imports)(adef.func)
    return root_model


MissionRootModel = _build_and_attach()
