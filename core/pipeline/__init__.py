"""core.pipeline — merge, scaffold, verify pipeline."""

from core.pipeline.merge import (
    GENERATED_DIR,
    MERGED_LOCK,
    MERGED_TOML,
    MergeConflict,
    MergeResult,
    is_merge_stale,
    merge,
)
from core.pipeline.scaffold import ScaffoldResult, scaffold_all, scaffold_system
from core.pipeline.verify import run_verify_core
from core.pipeline.veriq_project import build_project, evaluate_project_from_merged

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
