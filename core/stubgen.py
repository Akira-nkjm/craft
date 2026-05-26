"""stub 生成の filesystem・discovery 層。

`schema.stubgen` が担う純粋レンダリングに対して、このモジュールは
ファイル I/O と system discovery を加えた高レベル API を提供する:

    `generate_stubs(output_root=None) -> list[Path]` — 全 system を書き出す
    `check_stubs() -> list[tuple[Path, str]]` — 既存ファイルとの diff を返す
"""

import difflib
from pathlib import Path

from core.discovery import discover_systems
from core.paths import subsystem_dir
from schema.registry import UnifiedRegistry, default_registry
from schema.stubgen import STUB_FILENAME, _apply_ruff_format, render_subsystem_stub


def _stub_path_for(system: str, *, output_root: Path | None = None) -> Path:
    if output_root is None:
        return subsystem_dir(system) / STUB_FILENAME
    return output_root / system / STUB_FILENAME


def _ensure_bootstrap(registry: UnifiedRegistry | None) -> UnifiedRegistry:
    """default_registry を使う場合は system discovery を発火させる。"""
    if registry is not None:
        return registry
    discover_systems()
    return default_registry


def generate_stubs(
    *,
    output_root: Path | None = None,
    registry: UnifiedRegistry | None = None,
) -> list[Path]:
    """全 system の stub を生成し、書き込んだファイルパスのリストを返す。

    `output_root` を指定すると `<output_root>/<sub>/_stubs.pyi` に書き出す。
    省略時は `systems/<sub>/_stubs.pyi`。
    """
    reg = _ensure_bootstrap(registry)
    written: list[Path] = []
    for sub in sorted(reg.systems()):
        content = _apply_ruff_format(render_subsystem_stub(sub, registry=reg))
        path = _stub_path_for(sub, output_root=output_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def check_stubs(
    *,
    output_root: Path | None = None,
    registry: UnifiedRegistry | None = None,
) -> list[tuple[Path, str]]:
    """既存 stub と生成結果を比較し、ずれているファイル (path, diff) のリストを返す。

    diff は `difflib.unified_diff` 形式。出力が一致すれば空リスト。
    """
    reg = _ensure_bootstrap(registry)
    mismatches: list[tuple[Path, str]] = []
    for sub in sorted(reg.systems()):
        expected = _apply_ruff_format(render_subsystem_stub(sub, registry=reg))
        path = _stub_path_for(sub, output_root=output_root)
        actual = path.read_text(encoding="utf-8") if path.exists() else ""
        if actual != expected:
            diff = "".join(
                difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=str(path),
                    tofile=f"{path} (expected)",
                )
            )
            mismatches.append((path, diff))
    return mismatches
