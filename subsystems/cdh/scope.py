"""C&DH subsystem veriq scope。"""

import veriq as vq

from core.paths import subsystem_data_path
from schema import build_subsystem_root_model, default_registry
from subsystems.cdh import components as _components  # noqa: F401

cdh = vq.Scope("cdh")


def _build_and_attach() -> type:
    root_model = build_subsystem_root_model("cdh", subsystem_data_path("cdh"))
    cdh.root_model()(root_model)
    for adef in default_registry.analyses(subsystem="cdh"):
        if adef.verify:
            cdh.verification(adef.name)(adef.func)
        else:
            cdh.calculation(adef.name)(adef.func)
    return root_model


CdhRootModel = _build_and_attach()
