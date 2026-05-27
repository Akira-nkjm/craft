"""MCP tool handlers — registry / TOML / veriq の薄いラッパ。"""

import importlib
from typing import Any

from pydantic import ValidationError

from core.concurrency import ETagMode, resolve_expected_etag
from core.errors import ETagMismatch, PreconditionRequired
from core.instances import (
    InstanceNotFound,
    SingletonNotInstanceable,
    get_config_instance,
    get_instance,
    get_shared_spec,
    get_singleton_config,
    list_config_instances,
    list_instances,
    set_shared_spec,
)
from core.io.toml_io import read_toml
from core.operations import (
    create_component_op,
    delete_component_op,
    delete_config_entry_op,
    patch_component_op,
    patch_config_entry_op,
    set_config_entry_op,
    set_singleton_config_op,
)
from core.paths import MERGED_TOML, system_data_path
from core.persistence.history import (
    GitError,
    GitRefNotFound,
    git_diff,
    git_log,
)
from core.pipeline.merge import merge
from core.serialization import to_jsonable
from mcp_server.error_mapping import error_or_none
from schema import default_registry


def handle_list_introspection(kind: str) -> Any:
    """list_systems / list_components / list_configs / list_analyses。"""
    if kind == "systems":
        return sorted(default_registry.systems())
    if kind == "components":
        return [
            {
                "system": c.system,
                "name": c.name,
                "plural": c.plural,
                "cardinality": c.cardinality,
                "traits": list(c.traits),
            }
            for c in default_registry.components()
        ]
    if kind == "configs":
        return [
            {"system": c.system, "name": c.name, "plural": c.plural, "cardinality": c.cardinality}
            for c in default_registry.configs()
        ]
    if kind == "analyses":
        return [
            {
                "system": a.system,
                "name": a.name,
                "verify": a.verify,
                "desc": a.desc,
            }
            for a in default_registry.analyses()
        ]
    raise ValueError(f"Unknown introspection kind: {kind}")


def handle_get_schema(payload: dict[str, Any]) -> Any:
    system = payload.get("system", "")
    component = payload.get("component", "")
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        return {"error": f"component '{system}.{component}' not found"}
    return defn.entry.model_json_schema()


def handle_list_component_instances(system: str, component: str) -> Any:
    return list_instances(system, component)


def handle_get_component(system: str, component: str, instance: str | None) -> Any:
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        return {"error": f"component '{system}.{component}' not found"}
    if defn.cardinality == "single":
        data = read_toml(system_data_path(system))
        return data.get(defn.name, {"error": "no data"})
    if instance is None or not instance:
        return {"error": "name required for MultiInstance component"}
    try:
        payload, etag = get_instance(system, component, instance)
    except InstanceNotFound as e:
        return {"error": str(e)}
    return {"etag": etag, **payload}


def handle_get_config(system: str, name: str) -> Any:
    cfg = default_registry._configs.get((system, name))
    if cfg is None:
        return {"error": f"config '{system}.{name}' not found"}
    if cfg.cardinality == "multi":
        return list_config_instances(system, name)
    data, _ = get_singleton_config(system, name)
    return data


def handle_get_config_instance(system: str, name: str, key: str) -> Any:
    try:
        data, etag = get_config_instance(system, name, key)
    except InstanceNotFound as e:
        return {"error": str(e)}
    return {"etag": etag, **data}


def handle_set_config_instance(system: str, name: str, payload: dict[str, Any]) -> Any:
    key = payload.get("key", "")
    if not key:
        return {"error": "key required"}
    body = {k: v for k, v in payload.items() if k != "key"}
    try:
        result = set_config_entry_op(system, name, key, body, if_match=payload.get("etag"))
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}


def handle_patch_config_instance(system: str, name: str, payload: dict[str, Any]) -> Any:
    key = payload.get("key", "")
    if not key:
        return {"error": "key required"}
    delta = payload.get("delta") or {}
    if not isinstance(delta, dict):
        return {"error": "delta must be an object"}
    etag = payload.get("etag")
    auto_etag = bool(payload.get("auto_etag", False))
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: get_config_instance(system, name, key)[1]
        )
    except PreconditionRequired as e:
        return {"error": str(e)}
    except InstanceNotFound as e:
        return {"error": str(e)}
    try:
        result = patch_config_entry_op(system, name, key, delta, if_match=resolved_etag)
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}


def handle_delete_config_instance(system: str, name: str, payload: dict[str, Any]) -> Any:
    key = payload.get("key", "")
    if not key:
        return {"error": "key required"}
    etag = payload.get("etag")
    auto_etag = bool(payload.get("auto_etag", False))
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: get_config_instance(system, name, key)[1]
        )
    except PreconditionRequired as e:
        return {"error": str(e)}
    except InstanceNotFound as e:
        return {"error": str(e)}
    result = delete_config_entry_op(system, name, key, if_match=resolved_etag)
    if err := error_or_none(result):
        return err
    return {"deleted": True, "key": key}


# ─── write: instance CRUD ──────────────────────────────────────────


def handle_add_instance(system: str, component: str, payload: dict[str, Any]) -> Any:
    """MultiInstance への新規追加。`name` は payload から取り出す。"""
    name = payload.get("name", "")
    if not name:
        return {"error": "name required"}
    body = {k: v for k, v in payload.items() if k != "name"}
    try:
        result = create_component_op(system, component, name, body)
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}


def handle_patch_instance(system: str, component: str, payload: dict[str, Any]) -> Any:
    """multi: name 必須 / singleton: name 不要。auto_etag=true 時のみ ETag を自動取得。"""
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        return {"error": f"component '{system}.{component}' not found"}
    delta = payload.get("delta") or {}
    if not isinstance(delta, dict):
        return {"error": "delta must be an object"}

    if defn.cardinality == "multi":
        name = payload.get("name", "")
        if not name:
            return {"error": "name required for MultiInstance component"}
    else:
        name = ""

    etag = payload.get("etag")
    auto_etag = bool(payload.get("auto_etag", False))
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: get_instance(system, component, name)[1]
        )
    except PreconditionRequired as e:
        return {"error": str(e)}
    except InstanceNotFound as e:
        return {"error": str(e)}

    try:
        result = patch_component_op(system, component, name, delta, if_match=resolved_etag)
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}


def handle_delete_instance(system: str, component: str, payload: dict[str, Any]) -> Any:
    name = payload.get("name", "")
    if not name:
        return {"error": "name required"}
    etag = payload.get("etag")
    auto_etag = bool(payload.get("auto_etag", False))
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: get_instance(system, component, name)[1]
        )
    except PreconditionRequired as e:
        return {"error": str(e)}
    except InstanceNotFound as e:
        return {"error": str(e)}
    result = delete_component_op(system, component, name, if_match=resolved_etag)
    if err := error_or_none(result):
        return err
    return {"deleted": True, "name": name}


def handle_set_config(system: str, name: str, payload: dict[str, Any]) -> Any:
    """Singleton config 全置換。"""
    data_payload = payload.get("data")
    if not isinstance(data_payload, dict):
        return {"error": "data (object) required"}
    try:
        result = set_singleton_config_op(system, name, data_payload, if_match=payload.get("etag"))
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    if err := error_or_none(result):
        return err
    return {"etag": result.etag, **result.payload}


def handle_set_shared_spec(system: str, component: str, payload: dict[str, Any]) -> Any:
    """MultiInstance の shared spec 全置換。auto_etag=true 時のみ ETag を自動取得。"""
    spec = payload.get("spec")
    if not isinstance(spec, dict):
        return {"error": "spec (object) required"}
    etag = payload.get("etag")
    auto_etag = bool(payload.get("auto_etag", False))

    # spec が既に存在する場合のみ ETag policy を適用
    # 存在しない場合は新規作成のため etag 不要
    resolved_etag: str | None
    try:
        _, fetched_etag = get_shared_spec(system, component)
        mode: ETagMode = "auto" if auto_etag else "required"
        try:
            resolved_etag = resolve_expected_etag(etag, mode, fetch=lambda: fetched_etag)
        except PreconditionRequired as e:
            return {"error": str(e)}
    except InstanceNotFound:
        resolved_etag = etag  # 新規作成: etag 不要
    except SingletonNotInstanceable as e:
        return {"error": str(e)}

    try:
        new_spec, new_etag = set_shared_spec(system, component, spec, expected_etag=resolved_etag)
    except (ETagMismatch, PreconditionRequired) as e:
        return {"error": str(e)}
    except SingletonNotInstanceable as e:
        return {"error": str(e)}
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    return {"etag": new_etag, **new_spec}


# ─── history / diff ────────────────────────────────────────────────


def handle_history(payload: dict[str, Any]) -> Any:
    path = payload.get("path")
    limit_raw = payload.get("limit", 20)
    try:
        limit = int(limit_raw)
    except TypeError, ValueError:
        return {"error": "limit must be an integer"}
    try:
        entries = git_log(path, limit=limit)
    except GitRefNotFound as e:
        return {"error": f"ref_not_found: {e}"}
    except GitError as e:
        return {"error": f"git_error: {e}"}
    return {
        "path": path,
        "entries": [
            {"sha": e.sha, "author": e.author, "date": e.date, "message": e.message}
            for e in entries
        ],
    }


def handle_diff(payload: dict[str, Any]) -> Any:
    from_sha = payload.get("from")
    to_sha = payload.get("to")
    if not from_sha or not to_sha:
        return {"error": "from and to are required"}
    path = payload.get("path")
    try:
        diff_text = git_diff(from_sha, to_sha, path)
    except GitRefNotFound as e:
        return {"error": f"ref_not_found: {e}"}
    except GitError as e:
        return {"error": f"git_error: {e}"}
    return {"from": from_sha, "to": to_sha, "path": path, "diff": diff_text}


def handle_analysis(system: str | None, name: str, payload: dict[str, Any]) -> Any:
    """ad-hoc 関数を直接呼ぶ / veriq 経由なら evaluate して値を取り出す。"""
    adef = default_registry.analysis_or_none(system, name)
    if adef is None:
        return {"error": f"analysis '{system}.{name}' not found"}

    if adef.system is None:
        import inspect

        sig = inspect.signature(adef.func)
        try:
            bound = sig.bind_partial(**payload)
            bound.apply_defaults()
        except TypeError as e:
            return {"error": f"argument error: {e}"}
        value = adef.func(*bound.args, **bound.kwargs)
        return {"value": to_jsonable(value)}

    return _run_veriq_node(adef.system, adef.name, verify=False)


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
        mod = importlib.import_module(f"systems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is not None:
            project.add_scope(scope)
    return project
