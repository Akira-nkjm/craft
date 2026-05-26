"""Craft core — paths, TOML I/O, discovery, merge, scaffold。"""

from core.discovery import discover_subsystems
from core.merge import (
    GENERATED_DIR,
    MERGED_LOCK,
    MERGED_TOML,
    MergeConflict,
    MergeResult,
    is_merge_stale,
    merge,
)
from core.paths import (
    REPO_ROOT,
    subsystem_data_path,
    subsystem_dir,
    subsystems_root,
)
from core.scaffold import ScaffoldResult, scaffold_all, scaffold_subsystem
from core.toml_io import read_toml, write_toml_atomic

__all__ = [
    "GENERATED_DIR",
    "MERGED_LOCK",
    "MERGED_TOML",
    "MergeConflict",
    "MergeResult",
    "REPO_ROOT",
    "ScaffoldResult",
    "discover_subsystems",
    "is_merge_stale",
    "merge",
    "read_toml",
    "scaffold_all",
    "scaffold_subsystem",
    "subsystem_data_path",
    "subsystem_dir",
    "subsystems_root",
    "write_toml_atomic",
]
