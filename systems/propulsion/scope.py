"""propulsion system veriq scope。"""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry
from systems.propulsion import components as _components  # noqa: F401

propulsion = vq.Scope("propulsion")


def _build_and_attach() -> type:
    root_model = build_system_root_model("propulsion", system_data_path("propulsion"))
    propulsion.root_model()(root_model)
    for adef in default_registry.analyses(system="propulsion"):
        if adef.verify:
            propulsion.verification(adef.name)(adef.func)
        else:
            propulsion.calculation(adef.name)(adef.func)
    return root_model


PropulsionRootModel = _build_and_attach()
