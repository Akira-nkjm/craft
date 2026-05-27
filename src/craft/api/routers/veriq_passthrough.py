"""veriq pass-through API。

veriq CLI 機能のうち、graph / trace / schema 系を Python API 経由でラップして
HTTP で公開する。subprocess は使わない。

仕様: plan/Craft/01_仕様/API設計.md §veriq Pass-through API
"""

import importlib
from typing import Any

import veriq as vq
from fastapi import APIRouter, Query

from craft.api.errors import CraftAPIError, NotFoundError, ValidationFailedError
from craft.core.pipeline.merge import MERGED_TOML, MergeConflict, merge
from craft.schema import default_registry

router = APIRouter(prefix="/veriq", tags=["veriq"])


def _build_project() -> vq.Project:
    """登録済み system の scope を集めて Project を組み立てる。

    `api.routers.verify._build_project` と同等の動的 import パターン。
    """
    project = vq.Project("Craft")
    for sub in sorted(default_registry.systems()):
        mod = importlib.import_module(f"systems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is None:
            continue
        project.add_scope(scope)
    return project


def _node_payload(node_spec: vq.NodeSpec) -> dict[str, Any]:
    """NodeSpec を JSON 化可能な dict に変換。"""
    pp = node_spec.id
    return {
        "path": str(pp),
        "scope": pp.scope,
        "kind": node_spec.kind.value,
        "output_type": _type_name(node_spec.output_type),
        "is_input": _resolve_is_input(node_spec),
        "dependencies": sorted(str(dep) for dep in node_spec.dependencies),
        "param_mapping": {name: str(target) for name, target in node_spec.param_mapping.items()},
        "metadata": _jsonable(node_spec.metadata),
    }


def _resolve_is_input(node_spec: vq.NodeSpec) -> bool:
    """NodeSpec.is_input は veriq のバージョンによって method / property の差がある。

    どちらでも安全に bool を返す。
    """
    attr: Any = node_spec.is_input
    if callable(attr):
        return bool(attr())
    return bool(attr)


def _type_name(t: Any) -> str:
    if t is None:
        return "None"
    return getattr(t, "__name__", None) or repr(t)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in value]
    if isinstance(value, type):
        return _type_name(value)
    if callable(value):
        return repr(value)
    try:
        import json

        json.dumps(value)
        return value
    except TypeError, ValueError:
        return str(value)


@router.get("/scopes")
def list_scopes() -> dict[str, Any]:
    """登録済み scope の一覧と各 scope の calculation / verification 数。"""
    project = _build_project()
    scopes: list[dict[str, Any]] = []
    for name in sorted(project.scopes):
        scope = project.scopes[name]
        scopes.append(
            {
                "name": name,
                "calculations": sorted(scope._calculations.keys()),
                "verifications": sorted(scope._verifications.keys()),
                "requirements": sorted(scope._requirements.keys()),
                "calculation_count": len(scope._calculations),
                "verification_count": len(scope._verifications),
                "requirement_count": len(scope._requirements),
            }
        )
    return {"scopes": scopes}


@router.get("/nodes")
def list_nodes(
    kind: str | None = Query(default=None, description="MODEL / CALCULATION / VERIFICATION"),
    scope: str | None = Query(default=None, description="scope 名でフィルタ"),
) -> dict[str, Any]:
    """dependency graph の全ノード一覧。"""
    project = _build_project()
    spec = vq.build_graph_spec(project)

    node_kind: vq.NodeKind | None = None
    if kind is not None:
        try:
            node_kind = vq.NodeKind(kind.lower())
        except ValueError as e:
            allowed = [k.value for k in vq.NodeKind]
            raise ValidationFailedError(f"unknown kind '{kind}'; allowed: {allowed}") from e

    if scope is not None and scope not in spec.scope_names:
        raise ValidationFailedError(f"unknown scope '{scope}'; allowed: {list(spec.scope_names)}")

    nodes_iter: list[vq.NodeSpec]
    if node_kind is not None and scope is not None:
        nodes_iter = [n for n in spec.get_nodes_by_kind(node_kind) if n.id.scope == scope]
    elif node_kind is not None:
        nodes_iter = list(spec.get_nodes_by_kind(node_kind))
    elif scope is not None:
        nodes_iter = list(spec.get_nodes_in_scope(scope))
    else:
        nodes_iter = [spec.get_node(pp) for pp in spec.nodes]

    payload = [_node_payload(n) for n in nodes_iter]
    payload.sort(key=lambda d: d["path"])
    return {
        "total": len(payload),
        "filter": {"kind": kind, "scope": scope},
        "nodes": payload,
    }


@router.get("/nodes/{node_path:path}")
def get_node_detail(node_path: str) -> dict[str, Any]:
    """単一ノード詳細。node_path は `scope::path` 形式 (例: `power::?verify_battery_capacity`)。"""
    project = _build_project()
    spec = vq.build_graph_spec(project)

    target_pp: Any = None
    for pp in spec.nodes:
        if str(pp) == node_path:
            target_pp = pp
            break

    if target_pp is None:
        raise NotFoundError(f"node '{node_path}' not found in graph")

    node_spec = spec.get_node(target_pp)
    return _node_payload(node_spec)


@router.get("/trace")
def get_trace() -> dict[str, Any]:
    """traceability report (要求 ↔ verification マッピング)。"""
    project = _build_project()

    try:
        merge()
    except MergeConflict as e:
        raise CraftAPIError(f"merge failed: {e}") from e

    try:
        model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
        result = vq.evaluate_project(project, model_data)
    except Exception as e:  # veriq 内部例外を 500 として包む
        raise CraftAPIError(f"veriq evaluation failed: {e}") from e

    report = vq.build_traceability_report(project, result)

    requirements: list[dict[str, Any]] = []
    for entry in report.entries:
        requirements.append(
            {
                "requirement_id": entry.requirement_id,
                "scope": entry.scope_name,
                "description": entry.description,
                "status": entry.status.value
                if hasattr(entry.status, "value")
                else str(entry.status),
                "depth": entry.depth,
                "xfail": entry.xfail,
                "child_ids": list(entry.child_ids),
                "depends_on_ids": list(entry.depends_on_ids),
                "linked_verifications": [str(v) for v in entry.linked_verifications],
                "verification_results": _jsonable(entry.verification_results),
            }
        )

    return {
        "project_name": report.project_name,
        "summary": {
            "total_requirements": report.total_requirements,
            "satisfied": report.satisfied_count,
            "verified": report.verified_count,
            "failed": report.failed_count,
            "not_verified": report.not_verified_count,
        },
        "requirements": requirements,
    }


@router.get("/check")
def structural_check() -> dict[str, Any]:
    """構造妥当性チェック: project.input_model() が組み立て可能か。"""
    project = _build_project()
    try:
        model_cls = project.input_model()
    except Exception as e:
        return {
            "status": "error",
            "scopes": sorted(project.scopes.keys()),
            "detail": str(e),
        }
    return {
        "status": "ok",
        "scopes": sorted(project.scopes.keys()),
        "input_model": _type_name(model_cls),
    }


@router.get("/schema")
def input_schema() -> dict[str, Any]:
    """project.input_model() の JSON Schema。"""
    project = _build_project()
    try:
        model_cls = project.input_model()
    except Exception as e:
        raise CraftAPIError(f"failed to build input model: {e}") from e
    return model_cls.model_json_schema()
