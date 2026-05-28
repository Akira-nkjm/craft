"""Craft core — paths, TOML I/O, discovery, merge, scaffold。"""

from craft.core.discovery import discover_systems
from craft.core.io.toml_io import read_toml, write_toml_atomic
from craft.core.paths import (
    REPO_ROOT,
    subsystem_dir,
    subsystems_root,
    system_data_path,
)
from craft.core.pipeline.merge import (
    GENERATED_DIR,
    MERGED_LOCK,
    MERGED_TOML,
    MergeConflict,
    MergeResult,
    is_merge_stale,
    merge,
)
from craft.core.pipeline.scaffold import ScaffoldResult, scaffold_all, scaffold_system

__all__ = [
    "GENERATED_DIR",
    "MERGED_LOCK",
    "MERGED_TOML",
    "MergeConflict",
    "MergeResult",
    "REPO_ROOT",
    "ScaffoldResult",
    "discover_systems",
    "is_merge_stale",
    "merge",
    "read_toml",
    "scaffold_all",
    "scaffold_system",
    "system_data_path",
    "subsystem_dir",
    "subsystems_root",
    "write_toml_atomic",
]
