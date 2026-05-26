"""Shared veriq Project construction.

Single source of truth for building a vq.Project from the registry and
for running the merge → evaluate_project pipeline. All surface layers
(api, cli, mcp_server) must import from here instead of duplicating
these patterns.
"""

import importlib
from typing import Any

import veriq as vq

from schema import default_registry
from schema.registry import UnifiedRegistry


def build_project(registry: UnifiedRegistry = default_registry) -> vq.Project:
    """登録済み system の scope を集めて Project を組み立てる。"""
    project = vq.Project("Craft")
    for sub in sorted(registry.systems()):
        mod = importlib.import_module(f"systems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is None:
            continue
        project.add_scope(scope)
    return project


def evaluate_project_from_merged(
    registry: UnifiedRegistry = default_registry,
) -> tuple[vq.Project, Any]:
    """merge → evaluate_project を一括実行し (project, result) を返す。

    surface layer で "merge して veriq 評価したい" 場合はこれを使う。
    """
    from core.merge import MERGED_TOML, merge

    project = build_project(registry)
    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    return project, result
