"""AOCS fixture veriq scope."""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry

from . import components as _components  # noqa: F401

aocs = vq.Scope("aocs")


def _build_and_attach() -> type:
    root_model = build_system_root_model("aocs", system_data_path("aocs"))
    aocs.root_model()(root_model)
    for adef in default_registry.analyses(system="aocs"):
        if adef.verify:
            aocs.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            aocs.calculation(adef.name, imports=adef.imports)(adef.func)
    return root_model


AocsRootModel = _build_and_attach()
