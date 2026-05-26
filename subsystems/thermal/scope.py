"""Thermal subsystem veriq scope。"""

import veriq as vq

from core.paths import subsystem_data_path
from schema import build_subsystem_root_model, default_registry
from subsystems.thermal import components as _components  # noqa: F401

thermal = vq.Scope("thermal")


def _build_and_attach() -> type:
    root_model = build_subsystem_root_model("thermal", subsystem_data_path("thermal"))
    thermal.root_model()(root_model)
    for adef in default_registry.analyses(subsystem="thermal"):
        if adef.verify:
            thermal.verification(adef.name)(adef.func)
        else:
            thermal.calculation(adef.name)(adef.func)
    return root_model


ThermalRootModel = _build_and_attach()
