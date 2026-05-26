"""system 雛形生成。"""

from pathlib import Path

_HARDWARE_COMPONENTS = '''"""{name} system components."""

from schema import Component, MultiInstance, fld


class Example(Component, MultiInstance):
    """例: 任意の hardware component。必要に応じて trait を追加。"""

    rating: float = fld(ge=0, desc="例: 定格値")

    class Design:
        choice: str = fld(default="", desc="設計選択")
'''

_CONFIG_ONLY = '''"""{name} system configs."""

from schema import Config, fld


class Settings(Config):
    """例: 任意の設定値の塊。"""

    parameter: float = fld(ge=0)
'''

_SCOPE = '''"""{name} system veriq scope。"""

import veriq as vq

from core.paths import system_data_path
from schema import build_system_root_model, default_registry
{import_line}

{name} = vq.Scope("{name}")


def _build_and_attach() -> type:
    root_model = build_system_root_model("{name}", system_data_path("{name}"))
    {name}.root_model()(root_model)
    for adef in default_registry.analyses(system="{name}"):
        if adef.verify:
            {name}.verification(adef.name)(adef.func)
        else:
            {name}.calculation(adef.name)(adef.func)
    return root_model


{Name}RootModel = _build_and_attach()
'''

_DATA_TOML = """# {name} system data
# 簡略形式: `<sub>.model.` プレフィックス省略（merge 時に自動付与）

"""


def create_subsystem(target: Path, *, name: str, kind: str) -> None:
    """target ディレクトリに system 雛形ファイルを生成。"""
    target.mkdir(parents=True, exist_ok=False)
    (target / "__init__.py").write_text(f'"""{name} system package."""\n')

    if kind == "config-only":
        (target / "configs.py").write_text(_CONFIG_ONLY.format(name=name))
        import_line = f"from systems.{name} import configs as _configs  # noqa: F401"
    elif kind == "default":
        (target / "components.py").write_text(
            f'"""{name} system components."""\n'
            "\n"
            "# TODO: ここに `class X(Component, ...):` を書く\n"
        )
        import_line = f"from systems.{name} import components as _components  # noqa: F401"
    else:  # hardware
        (target / "components.py").write_text(_HARDWARE_COMPONENTS.format(name=name))
        import_line = f"from systems.{name} import components as _components  # noqa: F401"

    (target / "scope.py").write_text(
        _SCOPE.format(name=name, Name=name.capitalize(), import_line=import_line)
    )
    (target / "data.toml").write_text(_DATA_TOML.format(name=name))
