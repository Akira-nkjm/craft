"""Mission subsystem veriq scope。Config のみで構成。"""

import veriq as vq

from core.paths import subsystem_data_path
from schema import build_subsystem_root_model, default_registry
from subsystems.mission import configs as _configs  # noqa: F401

mission = vq.Scope("mission")


def _build_and_attach() -> type:
    root_model = build_subsystem_root_model("mission", subsystem_data_path("mission"))
    mission.root_model()(root_model)
    for adef in default_registry.analyses(subsystem="mission"):
        if adef.verify:
            mission.verification(adef.name)(adef.func)
        else:
            mission.calculation(adef.name)(adef.func)
    return root_model


MissionRootModel = _build_and_attach()
