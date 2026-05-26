"""POST /verify — veriq による検証を同期実行。

実行前に自動で `generated/merged.toml` を再生成し、それを veriq の入力とする。
"""

from typing import Any

import veriq as vq
from fastapi import APIRouter, HTTPException

from core.merge import MERGED_TOML, MergeConflict, merge

router = APIRouter(prefix="/verify", tags=["verify"])


def _build_project() -> vq.Project:
    """登録済み subsystem の scope を集めて Project を組み立てる。"""
    import importlib

    from schema import default_registry

    project = vq.Project("Craft")
    for sub in sorted(default_registry.subsystems()):
        mod = importlib.import_module(f"subsystems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is None:
            continue
        project.add_scope(scope)
    return project


@router.post("")
def run_verify() -> dict[str, Any]:
    project = _build_project()

    try:
        merge_result, _ = merge()
    except MergeConflict as e:
        raise HTTPException(status_code=409, detail=f"merge failed: {e}") from e

    try:
        model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
        result = vq.evaluate_project(project, model_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"veriq evaluation failed: {e}") from e

    scopes_payload: dict[str, dict[str, Any]] = {}
    for scope_name in result.scopes:
        tree = result.get_scope_tree(scope_name)
        if tree is None:
            scopes_payload[scope_name] = {"calculations": [], "verifications": []}
            continue
        scopes_payload[scope_name] = {
            "calculations": [
                {"path": str(node.path), "value": _jsonable(node.value)}
                for node in tree.calculations
            ],
            "verifications": [
                {"path": str(node.path), "value": _jsonable(node.value)}
                for node in tree.verifications
            ],
        }

    return {
        "success": result.success,
        "errors": [str(e) for e in result.errors],
        "merge": {
            "subsystems": list(merge_result.subsystems),
            "source_files": merge_result.source_files,
        },
        "scopes": scopes_payload,
    }


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value
