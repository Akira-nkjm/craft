"""Orbital system veriq scope。Config のみで構成。"""

import veriq as vq

from core.paths import system_data_path
from schema import build_system_root_model, default_registry
from systems.orbital import configs as _configs  # noqa: F401

orbital = vq.Scope("orbital")


def _build_and_attach() -> type:
    root_model = build_system_root_model("orbital", system_data_path("orbital"))
    orbital.root_model()(root_model)
    for adef in default_registry.analyses(system="orbital"):
        if adef.verify:
            orbital.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            orbital.calculation(adef.name, imports=adef.imports)(adef.func)
    return root_model


OrbitalRootModel = _build_and_attach()
