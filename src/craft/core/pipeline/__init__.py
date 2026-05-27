"""core.pipeline — merge, scaffold, verify pipeline."""

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
from craft.core.pipeline.verify import run_verify_core
from craft.core.pipeline.veriq_project import build_project, evaluate_project_from_merged

__all__ = [
    "GENERATED_DIR",
    "MERGED_LOCK",
    "MERGED_TOML",
    "MergeConflict",
    "MergeResult",
    "ScaffoldResult",
    "build_project",
    "evaluate_project_from_merged",
    "is_merge_stale",
    "merge",
    "run_verify_core",
    "scaffold_all",
    "scaffold_system",
]
