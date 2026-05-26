"""veriq CLI 用 project entrypoint。

`python -m veriq calc project:project -i generated/merged.toml` のように使う。

`discover_subsystems()` で全 subsystem を import し、scope を集めて Project に追加。
"""

import importlib

import veriq as vq

from core.discovery import discover_subsystems
from schema import default_registry


def build_project() -> vq.Project:
    """登録済み全 subsystem を集めて Project を組み立てる。

    `subsystems/<name>/scope.py` が `<name>` という名前の `vq.Scope` を公開している前提。
    """
    discover_subsystems()

    proj = vq.Project("Craft")
    for sub in sorted(default_registry.subsystems()):
        mod = importlib.import_module(f"subsystems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is None:
            raise RuntimeError(
                f"subsystems/{sub}/scope.py must expose a Scope variable named '{sub}'"
            )
        proj.add_scope(scope)
    return proj


project = build_project()
