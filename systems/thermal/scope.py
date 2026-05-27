"""Thermal system veriq scope。"""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry
from systems.thermal import components as _components  # noqa: F401

thermal = vq.Scope("thermal")


def _build_and_attach() -> type:
    root_model = build_system_root_model("thermal", system_data_path("thermal"))
    thermal.root_model()(root_model)
    for adef in default_registry.analyses(system="thermal"):
        if adef.verify:
            thermal.verification(adef.name)(adef.func)
        else:
            thermal.calculation(adef.name)(adef.func)
    return root_model


ThermalRootModel = _build_and_attach()
