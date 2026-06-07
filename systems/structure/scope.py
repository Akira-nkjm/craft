"""structure system veriq scope。

新サブシステムを足す時だけ触る。component / analysis 追加では編集不要。
"""

import veriq as vq

from craft.core.paths import system_data_path
from craft.schema import build_system_root_model, default_registry

# components / analyses を先に登録させる
from systems.structure import analyses as _analyses  # noqa: F401
from systems.structure import components as _components  # noqa: F401

structure = vq.Scope("structure")


def _build_and_attach() -> type:
    root_model = build_system_root_model("structure", system_data_path("structure"))
    structure.root_model()(root_model)
    for adef in default_registry.analyses(system="structure"):
        if adef.verify:
            structure.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            structure.calculation(adef.name, imports=adef.imports, transient=adef.transient)(
                adef.func
            )
    return root_model


StructureRootModel = _build_and_attach()
