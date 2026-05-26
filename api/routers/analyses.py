"""@analysis 自動 API 化。

- GET  /analyses                       — 登録済み解析一覧
- GET  /analyses/{subsystem}/{name}    — 単一解析のメタ情報
- POST /analyses/{subsystem}/{name}    — 解析実行
- POST /analyses/_/{name}              — ad-hoc 解析 (subsystem=None) 実行

仕様: plan/Craft/01_仕様/API設計.md §Analysis
仕様: plan/Craft/01_仕様/Analysis詳細仕様.md
"""

import inspect
from typing import Annotated, Any, get_args, get_origin

import veriq as vq
from fastapi import APIRouter, Body

from api.errors import NotFoundError
from core.merge import MERGED_TOML, merge
from schema import default_registry
from schema.registry import AnalysisDefinition

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _describe(adef: AnalysisDefinition) -> dict[str, Any]:
    sig = inspect.signature(adef.func)
    refs: list[dict[str, Any]] = []
    direct_params: list[dict[str, Any]] = []
    for param in sig.parameters.values():
        ref = _extract_ref(param.annotation)
        if ref is not None:
            refs.append(
                {
                    "name": param.name,
                    "ref": ref.path,
                    "scope": ref.scope,
                }
            )
        else:
            direct_params.append(
                {
                    "name": param.name,
                    "annotation": _safe_type_name(param.annotation),
                    "default": _safe_default(param.default),
                    "required": param.default is inspect.Parameter.empty,
                }
            )
    return {
        "name": adef.name,
        "subsystem": adef.subsystem,
        "verify": adef.verify,
        "imports": list(adef.imports),
        "cache": adef.cache,
        "desc": adef.desc,
        "return_annotation": _safe_type_name(sig.return_annotation),
        "ref_inputs": refs,
        "direct_inputs": direct_params,
        "adhoc": adef.subsystem is None,
    }


def _extract_ref(annotation: Any) -> vq.Ref | None:
    if get_origin(annotation) is Annotated:
        for arg in get_args(annotation)[1:]:
            if isinstance(arg, vq.Ref):
                return arg
    return None


def _safe_type_name(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty or annotation is inspect.Signature.empty:
        return "Any"
    return getattr(annotation, "__name__", None) or repr(annotation)


def _safe_default(default: Any) -> Any:
    if default is inspect.Parameter.empty:
        return None
    try:
        # JSON 化可能な簡単な値か
        import json

        json.dumps(default)
        return default
    except TypeError, ValueError:
        return str(default)


@router.get("")
def list_analyses() -> dict[str, Any]:
    items = [_describe(a) for a in default_registry.analyses()]
    return {"analyses": items}


@router.get("/{subsystem}/{name}")
def get_analysis(subsystem: str, name: str) -> dict[str, Any]:
    sub = None if subsystem == "_" else subsystem
    adef = default_registry.analysis_or_none(sub, name)
    if adef is None:
        raise NotFoundError(f"Analysis '{subsystem}.{name}' not found")
    return _describe(adef)


@router.post("/{subsystem}/{name}")
def run_analysis(
    subsystem: str,
    name: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    sub = None if subsystem == "_" else subsystem
    adef = default_registry.analysis_or_none(sub, name)
    if adef is None:
        raise NotFoundError(f"Analysis '{subsystem}.{name}' not found")

    if adef.subsystem is None:
        return _run_adhoc(adef, payload)
    return _run_via_veriq(adef)


def _run_adhoc(adef: AnalysisDefinition, payload: dict[str, Any]) -> dict[str, Any]:
    """ad-hoc: 関数を直接呼ぶ。payload は signature にバインド。"""
    sig = inspect.signature(adef.func)
    try:
        bound = sig.bind_partial(**payload)
        bound.apply_defaults()
    except TypeError as e:
        from api.errors import ValidationFailedError

        raise ValidationFailedError(str(e)) from e
    value = adef.func(*bound.args, **bound.kwargs)
    return {
        "analysis": adef.name,
        "subsystem": adef.subsystem,
        "value": _jsonable(value),
    }


def _run_via_veriq(adef: AnalysisDefinition) -> dict[str, Any]:
    """veriq 経由: merge → evaluate_project → 該当ノード値を返す。"""
    import importlib

    assert adef.subsystem is not None, "non-veriq analysis routed to veriq path"
    project = vq.Project("Craft")
    for sub in sorted(default_registry.subsystems()):
        mod = importlib.import_module(f"subsystems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is None:
            continue
        project.add_scope(scope)
    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    tree = result.get_scope_tree(adef.subsystem)
    if tree is None:
        return {"analysis": adef.name, "subsystem": adef.subsystem, "value": None}

    nodes = tree.verifications if adef.verify else tree.calculations
    prefix = "?" if adef.verify else "@"
    for node in nodes:
        if str(node.path).endswith(f"{prefix}{adef.name}"):
            return {
                "analysis": adef.name,
                "subsystem": adef.subsystem,
                "verify": adef.verify,
                "value": _jsonable(node.value),
            }
    return {
        "analysis": adef.name,
        "subsystem": adef.subsystem,
        "verify": adef.verify,
        "value": None,
    }


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value
