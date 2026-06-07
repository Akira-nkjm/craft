"""aocs system veriq scope。

新サブシステムを足す時だけ触る。component / analysis 追加では編集不要。
analyses を追加した場合は import を追加すること。
"""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry
from systems.aocs import analyses as _analyses  # noqa: F401
from systems.aocs import components as _components  # noqa: F401
from systems.aocs import configs as _configs  # noqa: F401

aocs = vq.Scope("aocs")


def _build_and_attach() -> type:
    root_model = build_system_root_model("aocs", system_data_path("aocs"))
    aocs.root_model()(root_model)
    for adef in default_registry.analyses(system="aocs"):
        if adef.verify:
            aocs.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            aocs.calculation(adef.name, imports=adef.imports, transient=adef.transient)(adef.func)
    return root_model


AocsRootModel = _build_and_attach()
