"""Power system veriq scope。

新サブシステムを足す時だけ触る。component / analysis 追加では編集不要。
"""

import veriq as vq

from core.paths import system_data_path
from schema import build_system_root_model, default_registry

# components / analyses を先に登録させる
from systems.power import analyses as _analyses  # noqa: F401
from systems.power import components as _components  # noqa: F401

power = vq.Scope("power")


def _build_and_attach() -> type:
    """root model を組み立てて scope に紐付け、analysis を verification/calculation に貼り直す。"""
    root_model = build_system_root_model("power", system_data_path("power"))
    power.root_model()(root_model)

    for adef in default_registry.analyses(system="power"):
        if adef.verify:
            power.verification(adef.name, imports=adef.imports)(adef.func)
        else:
            power.calculation(adef.name, imports=adef.imports)(adef.func)
    return root_model


PowerRootModel = _build_and_attach()
