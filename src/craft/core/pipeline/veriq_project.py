"""Shared veriq Project construction.

Single source of truth for building a vq.Project from the registry and
for running the merge → evaluate_project pipeline. All surface layers
(api, cli, mcp_server) must import from here instead of duplicating
these patterns.
"""

from typing import Any

import veriq as vq

from craft.core.discovery import get_scope
from craft.core.paths import system_data_path
from craft.schema import default_registry
from craft.schema.registry import UnifiedRegistry


def build_project(registry: UnifiedRegistry = default_registry) -> vq.Project:
    """登録済み system の scope を集めて Project を組み立てる。"""
    project = vq.Project("Craft")
    for sub in sorted(registry.systems()):
        scope = get_scope(sub)
        if scope is None:
            continue
        project.add_scope(scope)
    return project


def build_project_with_scope_input(
    registry: UnifiedRegistry = default_registry,
) -> vq.Project:
    """各 scope に systems/<name>/data.toml を input として割り当てて Project を組む。

    veriq の `Scope(input=...)` 機構を使い、merge を介さず各 data.toml を直接
    ロードできるようにする。`build_project` との違いは scope.input を設定する点のみ。
    """
    project = vq.Project("Craft")
    for sub in sorted(registry.systems()):
        scope = get_scope(sub)
        if scope is None:
            continue
        scope.input = system_data_path(sub)  # 絶対パス → veriq が直接ロード
        project.add_scope(scope)
    return project


def evaluate_project_from_merged(
    registry: UnifiedRegistry = default_registry,
) -> tuple[vq.Project, Any]:
    """merge → evaluate_project を一括実行し (project, result) を返す。

    surface layer で "merge して veriq 評価したい" 場合はこれを使う。
    """
    from craft.core.pipeline.merge import MERGED_TOML, merge

    project = build_project(registry)
    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    return project, result


def evaluate_project_via_scope_input(
    registry: UnifiedRegistry = default_registry,
) -> tuple[vq.Project, Any]:
    """scope-input 経路で評価し (project, result) を返す。

    `evaluate_project_from_merged` と同じ結果を返すが、generated/merged.toml を
    生成せず、各 scope の data.toml を veriq が直接合成する（merge 不要）。
    """
    project = build_project_with_scope_input(registry)
    model_data = vq.load_model_data(project)
    result = vq.evaluate_project(project, model_data)
    return project, result
