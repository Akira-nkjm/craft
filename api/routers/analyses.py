"""@analysis 自動 API 化。

- GET  /analyses                       — 登録済み解析一覧
- GET  /analyses/{system}/{name}    — 単一解析のメタ情報
- POST /analyses/{system}/{name}    — 解析実行
- POST /analyses/_/{name}              — ad-hoc 解析 (system=None) 実行

仕様: plan/Craft/01_仕様/API設計.md §Analysis
仕様: plan/Craft/01_仕様/Analysis詳細仕様.md
"""

import inspect
from typing import Annotated, Any, get_args, get_origin

import veriq as vq
from fastapi import APIRouter, Body

from api.errors import NotFoundError, ValidationFailedError
from core.analysis_runner import AnalysisArgumentError, AnalysisNotFound
from core.analysis_runner import run_analysis as _run_analysis
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
        "system": adef.system,
        "verify": adef.verify,
        "imports": list(adef.imports),
        "cache": adef.cache,
        "desc": adef.desc,
        "return_annotation": _safe_type_name(sig.return_annotation),
        "ref_inputs": refs,
        "direct_inputs": direct_params,
        "adhoc": adef.system is None,
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
        import json

        json.dumps(default)
        return default
    except TypeError, ValueError:
        return str(default)


@router.get("")
def list_analyses() -> dict[str, Any]:
    items = [_describe(a) for a in default_registry.analyses()]
    return {"analyses": items}


@router.get("/{system}/{name}")
def get_analysis(system: str, name: str) -> dict[str, Any]:
    sub = None if system == "_" else system
    adef = default_registry.analysis_or_none(sub, name)
    if adef is None:
        raise NotFoundError(f"Analysis '{system}.{name}' not found")
    return _describe(adef)


@router.post("/{system}/{name}")
def run_analysis_endpoint(
    system: str,
    name: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    sub = None if system == "_" else system
    try:
        result = _run_analysis(sub, name, payload)
    except AnalysisNotFound as e:
        raise NotFoundError(str(e)) from e
    except AnalysisArgumentError as e:
        raise ValidationFailedError(str(e)) from e

    output: dict[str, Any] = {
        "analysis": result.name,
        "system": result.system,
        "value": result.value,
    }
    if result.cache_hit is not None:
        output["cache_hit"] = result.cache_hit
    if result.system is not None:
        output["verify"] = result.verify
    return output
