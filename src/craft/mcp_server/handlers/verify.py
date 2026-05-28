"""Verification MCP tool handlers."""

from typing import Any

from craft.core.discovery import get_scope
from craft.core.paths import MERGED_TOML
from craft.core.pipeline.merge import merge
from craft.core.serialization import to_jsonable
from craft.schema import default_registry


def handle_verify_single(system: str | None, name: str) -> Any:
    if system is None:
        return {"error": "verify_* tools require veriq-attached analysis"}
    return _run_veriq_node(system, name, verify=True)


def handle_verify_all() -> Any:
    """全 scope を評価して calculation / verification を返す。"""
    import veriq as vq

    project = _build_project()
    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    out: dict[str, Any] = {"success": result.success, "errors": [str(e) for e in result.errors]}
    scopes: dict[str, Any] = {}
    for scope_name in result.scopes:
        tree = result.get_scope_tree(scope_name)
        if tree is None:
            scopes[scope_name] = {"calculations": [], "verifications": []}
            continue
        scopes[scope_name] = {
            "calculations": [
                {"path": str(node.path), "value": to_jsonable(node.value)}
                for node in tree.calculations
            ],
            "verifications": [
                {"path": str(node.path), "value": to_jsonable(node.value)}
                for node in tree.verifications
            ],
        }
    out["scopes"] = scopes
    return out


def _run_veriq_node(system: str, name: str, *, verify: bool) -> Any:
    import veriq as vq

    project = _build_project()
    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    tree = result.get_scope_tree(system)
    if tree is None:
        return {"value": None}
    nodes = tree.verifications if verify else tree.calculations
    prefix = "?" if verify else "@"
    for node in nodes:
        if str(node.path).endswith(f"{prefix}{name}"):
            return {"value": to_jsonable(node.value)}
    return {"value": None, "note": "node not found in evaluation result"}


def _build_project():
    import veriq as vq

    project = vq.Project("Craft")
    for sub in sorted(default_registry.systems()):
        scope = get_scope(sub)
        if scope is not None:
            project.add_scope(scope)
    return project
