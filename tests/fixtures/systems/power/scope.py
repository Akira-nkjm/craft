"""Power fixture veriq scope."""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry

from . import analyses as _analyses  # noqa: F401
from . import components as _components  # noqa: F401

power = vq.Scope("power")


def _build_and_attach() -> type:
    root_model = build_system_root_model("power", system_data_path("power"))
    power.root_model()(root_model)
    for adef in default_registry.analyses(system="power"):
        if adef.verify:
            power.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            power.calculation(adef.name, imports=adef.imports)(adef.func)
    return root_model


PowerRootModel = _build_and_attach()
