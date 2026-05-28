"""ff system veriq scope。"""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry
from systems.ff import components as _components  # noqa: F401

ff = vq.Scope("ff")


def _build_and_attach() -> type:
    root_model = build_system_root_model("ff", system_data_path("ff"))
    ff.root_model()(root_model)
    for adef in default_registry.analyses(system="ff"):
        if adef.verify:
            ff.verification(adef.name)(adef.func)
        else:
            ff.calculation(adef.name)(adef.func)
    return root_model


FfRootModel = _build_and_attach()
