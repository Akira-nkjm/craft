"""Power subsystem veriq scope。

新サブシステムを足す時だけ触る。component / analysis 追加では編集不要。
"""

import veriq as vq

from core.paths import subsystem_data_path
from schema import build_subsystem_root_model, default_registry

# components / analyses を先に登録させる
from subsystems.power import analyses as _analyses  # noqa: F401
from subsystems.power import components as _components  # noqa: F401

power = vq.Scope("power")


def _build_and_attach() -> type:
    """root model を組み立てて scope に紐付け、analysis を verification/calculation に貼り直す。"""
    root_model = build_subsystem_root_model("power", subsystem_data_path("power"))
    power.root_model()(root_model)

    for adef in default_registry.analyses(subsystem="power"):
        if adef.verify:
            power.verification(adef.name)(adef.func)
        else:
            power.calculation(adef.name)(adef.func)
    return root_model


PowerRootModel = _build_and_attach()
