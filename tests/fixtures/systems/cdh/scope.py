"""C&DH fixture veriq scope."""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry

from . import components as _components  # noqa: F401

cdh = vq.Scope("cdh")


def _build_and_attach() -> type:
    root_model = build_system_root_model("cdh", system_data_path("cdh"))
    cdh.root_model()(root_model)
    for adef in default_registry.analyses(system="cdh"):
        if adef.verify:
            cdh.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            cdh.calculation(adef.name, imports=adef.imports)(adef.func)
    return root_model


CdhRootModel = _build_and_attach()
