"""Orbital subsystem veriq scope。Config のみで構成。"""

import veriq as vq

from core.paths import subsystem_data_path
from schema import build_subsystem_root_model, default_registry
from subsystems.orbital import configs as _configs  # noqa: F401

orbital = vq.Scope("orbital")


def _build_and_attach() -> type:
    root_model = build_subsystem_root_model("orbital", subsystem_data_path("orbital"))
    orbital.root_model()(root_model)
    for adef in default_registry.analyses(subsystem="orbital"):
        if adef.verify:
            orbital.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            orbital.calculation(adef.name, imports=adef.imports)(adef.func)
    return root_model


OrbitalRootModel = _build_and_attach()
