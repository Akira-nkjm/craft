from pathlib import Path

import pytest

import craft.core.discovery as discovery
from craft.schema.registry import default_registry


def _module_not_found(name: str) -> ModuleNotFoundError:
    return ModuleNotFoundError(f"No module named '{name}'", name=name)


def test_discover_existing_systems_imports_default_root() -> None:
    # conftest の autouse fixture が fixture systems を pre-load しているので、
    # 実 systems を package mode で再 import すると DuplicateRegistration になる。
    # この test は discover_systems の返り値（system 名一覧）のみ検証するため、
    # 一旦 registry を空にしてから実行する（fixture の restore は finally で行われる）。
    default_registry.clear()

    systems_root = Path("systems")
    expected = sorted(
        sub_dir.name
        for sub_dir in systems_root.iterdir()
        if sub_dir.is_dir()
        and not sub_dir.name.startswith("_")
        and not sub_dir.name.startswith(".")
    )

    assert discovery.discover_systems(root=systems_root) == expected


def test_package_import_raises_for_nested_module_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    systems_root = tmp_path / "systems"
    (systems_root / "broken").mkdir(parents=True)

    def import_module(name: str) -> object:
        if name == "systems.broken":
            return object()
        if name == "systems.broken.components":
            raise _module_not_found("nonexistent_dependency_for_discovery_test")
        raise _module_not_found(name)

    monkeypatch.setattr(discovery.importlib, "import_module", import_module)

    with pytest.raises(
        ModuleNotFoundError,
        match="Failed to import system 'broken' file 'components'",
    ) as exc_info:
        discovery.discover_systems(root=systems_root)

    cause = exc_info.value.__cause__
    assert isinstance(cause, ModuleNotFoundError)
    assert cause.name == "nonexistent_dependency_for_discovery_test"


def test_package_import_ignores_missing_ordered_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    systems_root = tmp_path / "systems"
    (systems_root / "empty").mkdir(parents=True)

    def import_module(name: str) -> object:
        if name == "systems.empty":
            return object()
        raise _module_not_found(name)

    monkeypatch.setattr(discovery.importlib, "import_module", import_module)

    assert discovery.discover_systems(root=systems_root) == ["empty"]


def test_discover_raises_for_module_not_found_inside_system_file(
    tmp_path: Path,
) -> None:
    systems_root = tmp_path / "systems"
    broken = systems_root / "broken"
    broken.mkdir(parents=True)
    (broken / "components.py").write_text(
        "from nonexistent_dependency_for_discovery_test import X\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ModuleNotFoundError,
        match="Failed to import system 'broken' file 'components'",
    ) as exc_info:
        discovery.discover_systems(root=systems_root)

    assert exc_info.value.__cause__ is not None


def test_discover_ignores_missing_ordered_files(tmp_path: Path) -> None:
    systems_root = tmp_path / "systems"
    empty = systems_root / "empty"
    empty.mkdir(parents=True)
    (empty / "components.py").write_text("", encoding="utf-8")

    assert discovery.discover_systems(root=systems_root) == ["empty"]
