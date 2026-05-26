"""Analysis execution runner — eliminates duplication across API / CLI / MCP."""

import inspect
from dataclasses import dataclass
from typing import Any

from core.analysis_cache import (
    code_version_for_func,
    compute_cache_key,
    get_cached,
    put_cached,
)
from core.errors import AnalysisArgumentError, AnalysisNotFound
from core.serialization import to_jsonable
from schema import default_registry
from schema.registry import AnalysisDefinition


@dataclass
class AnalysisRunResult:
    """Result of running a single analysis."""

    name: str
    system: str | None
    value: Any  # already JSON-serializable (to_jsonable applied)
    verify: bool
    cache_hit: bool | None  # None = no cache capability; False = miss; True = hit


def run_analysis(
    system: str | None,
    name: str,
    payload: dict[str, Any],
    *,
    use_cache: bool = True,
) -> AnalysisRunResult:
    """Execute a registered analysis and return a structured result.

    Raises:
        AnalysisNotFound: if (system, name) is not registered.
        AnalysisArgumentError: if payload does not match the function signature.
    """
    adef = default_registry.analysis_or_none(system, name)
    if adef is None:
        sys_str = system or "_"
        raise AnalysisNotFound(f"Analysis '{sys_str}.{name}' not found")

    if adef.system is None:
        return _run_adhoc(adef, payload, use_cache=use_cache)
    return _run_via_veriq(adef)


def extract_analysis_value(result: Any, system: str, name: str, *, verify: bool) -> Any | None:
    """Extract a named analysis node value from a veriq evaluation result.

    Args:
        result: vq.EvaluationResult returned by evaluate_project_from_merged().
        system: scope name.
        name: analysis name.
        verify: True for verification nodes, False for calculation nodes.

    Returns:
        JSON-serializable value, or None if the scope or node is not found.
    """
    tree = result.get_scope_tree(system)
    if tree is None:
        return None
    nodes = tree.verifications if verify else tree.calculations
    prefix = "?" if verify else "@"
    for node in nodes:
        if str(node.path).endswith(f"{prefix}{name}"):
            return to_jsonable(node.value)
    return None


def _run_adhoc(
    adef: AnalysisDefinition,
    payload: dict[str, Any],
    *,
    use_cache: bool,
) -> AnalysisRunResult:
    sig = inspect.signature(adef.func)
    try:
        bound = sig.bind_partial(**payload)
        bound.apply_defaults()
    except TypeError as e:
        raise AnalysisArgumentError(str(e)) from e

    inputs = dict(bound.arguments)
    cache_key: str | None = None

    if adef.cache and use_cache:
        code_version = code_version_for_func(adef.func)
        cache_key = compute_cache_key(adef.name, code_version, inputs)
        cached = get_cached(adef.name, cache_key)
        if cached is not None:
            return AnalysisRunResult(
                name=adef.name,
                system=adef.system,
                value=cached.get("value"),
                verify=adef.verify,
                cache_hit=True,
            )

    value = adef.func(*bound.args, **bound.kwargs)
    json_value = to_jsonable(value)

    if cache_key is not None:
        put_cached(adef.name, cache_key, {"value": json_value})

    return AnalysisRunResult(
        name=adef.name,
        system=adef.system,
        value=json_value,
        verify=adef.verify,
        cache_hit=False if adef.cache else None,
    )


def _run_via_veriq(adef: AnalysisDefinition) -> AnalysisRunResult:
    assert adef.system is not None
    from core.veriq_project import evaluate_project_from_merged

    _, result = evaluate_project_from_merged()
    value = extract_analysis_value(result, adef.system, adef.name, verify=adef.verify)

    return AnalysisRunResult(
        name=adef.name,
        system=adef.system,
        value=value,
        verify=adef.verify,
        cache_hit=None,
    )
