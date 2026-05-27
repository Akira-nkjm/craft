"""Merge engine — systems/*/data.toml → generated/merged.toml。

仕様: plan/Craft/01_仕様/データパイプライン.md §3
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from craft.core.io.toml_io import read_toml, write_toml_atomic
from craft.core.paths import (
    GENERATED_DIR,
    MERGED_LOCK,
    MERGED_TOML,
    REPO_ROOT,
    subsystems_root,
    system_data_path,
)

# Re-export path constants for backward compatibility.
__all__ = [
    "GENERATED_DIR",
    "MERGED_LOCK",
    "MERGED_TOML",
    "MergeConflict",
    "MergeResult",
    "is_merge_stale",
    "merge",
]


class MergeConflict(Exception):  # noqa: N818
    """同一 top-level key が複数 system で出現した。"""


@dataclass(frozen=True, slots=True)
class MergeResult:
    output_path: Path
    source_files: dict[str, str] = field(default_factory=dict)
    systems: tuple[str, ...] = ()
    written: bool = True


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _discover_data_files(only: list[str] | None = None) -> list[tuple[str, Path]]:
    """`systems/<name>/data.toml` が存在するものを返す（system 名昇順）。"""
    root = subsystems_root()
    if not root.exists():
        return []
    pairs: list[tuple[str, Path]] = []
    for sub_dir in sorted(root.iterdir()):
        if not sub_dir.is_dir() or sub_dir.name.startswith(("_", ".")):
            continue
        if only is not None and sub_dir.name not in only:
            continue
        data = system_data_path(sub_dir.name)
        if data.exists():
            pairs.append((sub_dir.name, data))
    return pairs


def merge(
    *,
    systems: list[str] | None = None,
    output_path: Path | None = None,
    dry_run: bool = False,
) -> tuple[MergeResult, dict[str, Any]]:
    """全 system の data.toml を統合。

    Args:
        systems: 対象 system 名のリスト。None なら全件。
        output_path: 出力先（default `generated/merged.toml`）。
        dry_run: True なら書き込まず dict のみ返す。

    Returns:
        (MergeResult, merged_dict)
    """
    out_path = output_path or MERGED_TOML
    pairs = _discover_data_files(systems)

    merged: dict[str, Any] = {}
    source_files: dict[str, str] = {}
    subsystem_names: list[str] = []

    for sub_name, data_path in pairs:
        data = read_toml(data_path)
        # data.toml は `<sub>.model.` プレフィックス省略の簡略形式で書く。
        # merge 時に `[<sub>.model.<...>]` の veriq 規約に自動的に詰め直す。
        if sub_name in merged:
            raise MergeConflict(f"Subsystem '{sub_name}' already merged (duplicate data.toml?)")
        merged[sub_name] = {"model": data}
        source_files[str(data_path.relative_to(REPO_ROOT))] = _sha256_file(data_path)
        subsystem_names.append(sub_name)

    result = MergeResult(
        output_path=out_path,
        source_files=source_files,
        systems=tuple(subsystem_names),
        written=not dry_run,
    )

    if not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_toml_atomic(out_path, merged)
        _write_lock(MERGED_LOCK, source_files)

    return result, merged


def _write_lock(lock_path: Path, source_files: dict[str, str]) -> None:
    """`merged.lock` に sha256 一覧を書く。"""
    payload = {
        "version": 1,
        "sources": {path: {"sha256": digest} for path, digest in sorted(source_files.items())},
    }
    write_toml_atomic(lock_path, payload)


def is_merge_stale() -> bool:
    """`merged.lock` を見て、元 data.toml が変更されていれば True。"""
    if not MERGED_LOCK.exists():
        return True
    lock = read_toml(MERGED_LOCK)
    sources = lock.get("sources", {})
    current = {str(p.relative_to(REPO_ROOT)): _sha256_file(p) for _, p in _discover_data_files()}
    return current != {k: v.get("sha256") for k, v in sources.items()}
