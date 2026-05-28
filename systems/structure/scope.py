"""structure system veriq scope。"""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry
from systems.structure import components as _components  # noqa: F401

structure = vq.Scope("structure")


def _build_and_attach() -> type:
    root_model = build_system_root_model("structure", system_data_path("structure"))
    structure.root_model()(root_model)
    for adef in default_registry.analyses(system="structure"):
        if adef.verify:
            structure.verification(adef.name)(adef.func)
        else:
            structure.calculation(adef.name)(adef.func)
    return root_model


StructureRootModel = _build_and_attach()
