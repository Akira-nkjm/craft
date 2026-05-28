"""comm system veriq scope。"""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry
from systems.comm import components as _components  # noqa: F401

comm = vq.Scope("comm")


def _build_and_attach() -> type:
    root_model = build_system_root_model("comm", system_data_path("comm"))
    comm.root_model()(root_model)
    for adef in default_registry.analyses(system="comm"):
        if adef.verify:
            comm.verification(adef.name)(adef.func)
        else:
            comm.calculation(adef.name)(adef.func)
    return root_model


CommRootModel = _build_and_attach()
