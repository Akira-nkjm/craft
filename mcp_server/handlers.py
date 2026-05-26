"""MCP tool handlers — registry / TOML / veriq の薄いラッパ。"""

import importlib
from typing import Any

from pydantic import ValidationError

from core.history import (
    GitError,
    GitRefNotFound,
    git_diff,
    git_log,
)
from core.instances import (
    InstanceAlreadyExists,
    InstanceNotFound,
    SharedSpecConflict,
    SingletonNotInstanceable,
    create_instance,
    delete_instance,
    get_instance,
    get_shared_spec,
    list_instances,
    patch_instance,
    set_shared_spec,
)
from core.merge import MERGED_TOML, merge
from core.paths import subsystem_data_path
from core.toml_io import read_toml, write_toml_atomic
from schema import default_registry


def handle_list_introspection(kind: str) -> Any:
    """list_subsystems / list_components / list_configs / list_analyses。"""
    if kind == "subsystems":
        return sorted(default_registry.subsystems())
    if kind == "components":
        return [
            {
                "subsystem": c.subsystem,
                "name": c.name,
                "plural": c.plural,
                "cardinality": c.cardinality,
                "traits": list(c.traits),
            }
            for c in default_registry.components()
        ]
    if kind == "configs":
        return [{"subsystem": c.subsystem, "name": c.name} for c in default_registry.configs()]
    if kind == "analyses":
        return [
            {
                "subsystem": a.subsystem,
                "name": a.name,
                "verify": a.verify,
                "desc": a.desc,
            }
            for a in default_registry.analyses()
        ]
    raise ValueError(f"Unknown introspection kind: {kind}")


def handle_get_schema(payload: dict[str, Any]) -> Any:
    subsystem = payload.get("subsystem", "")
    component = payload.get("component", "")
    defn = default_registry.component_or_none(subsystem, component)
    if defn is None:
        return {"error": f"component '{subsystem}.{component}' not found"}
    return defn.entry.model_json_schema()


def handle_list_component_instances(subsystem: str, component: str) -> Any:
    return list_instances(subsystem, component)


def handle_get_component(subsystem: str, component: str, instance: str | None) -> Any:
    defn = default_registry.component_or_none(subsystem, component)
    if defn is None:
        return {"error": f"component '{subsystem}.{component}' not found"}
    if defn.cardinality == "single":
        data = read_toml(subsystem_data_path(subsystem))
        return data.get(defn.name, {"error": "no data"})
    if instance is None or not instance:
        return {"error": "name required for MultiInstance component"}
    try:
        payload, etag = get_instance(subsystem, component, instance)
    except InstanceNotFound as e:
        return {"error": str(e)}
    return {"etag": etag, **payload}


def handle_get_config(subsystem: str, name: str) -> Any:
    data = read_toml(subsystem_data_path(subsystem))
    return data.get(name, {"error": f"config '{subsystem}.{name}' not present in data.toml"})


# ─── write: instance CRUD ──────────────────────────────────────────


def handle_add_instance(subsystem: str, component: str, payload: dict[str, Any]) -> Any:
    """MultiInstance への新規追加。`name` は payload から取り出す。"""
    name = payload.get("name", "")
    if not name:
        return {"error": "name required"}
    body = {k: v for k, v in payload.items() if k != "name"}
    try:
        view, etag = create_instance(subsystem, component, name, body)
    except InstanceAlreadyExists as e:
        return {"error": str(e)}
    except InstanceNotFound as e:
        return {"error": str(e)}
    except SingletonNotInstanceable as e:
        return {"error": str(e)}
    except SharedSpecConflict as e:
        return {"error": str(e)}
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    return {"etag": etag, **view}


def handle_patch_instance(subsystem: str, component: str, payload: dict[str, Any]) -> Any:
    """multi: name 必須 / singleton: name 不要。etag 省略時は内部で補完。"""
    defn = default_registry.component_or_none(subsystem, component)
    if defn is None:
        return {"error": f"component '{subsystem}.{component}' not found"}
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
    if etag is None:
        try:
            _, etag = get_instance(subsystem, component, name)
        except InstanceNotFound as e:
            return {"error": str(e)}

    try:
        view, new_etag = patch_instance(subsystem, component, name, delta, expected_etag=etag)
    except InstanceNotFound as e:
        return {"error": str(e)}
    except SharedSpecConflict as e:
        return {"error": str(e)}
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    return {"etag": new_etag, **view}


def handle_delete_instance(subsystem: str, component: str, payload: dict[str, Any]) -> Any:
    name = payload.get("name", "")
    if not name:
        return {"error": "name required"}
    etag = payload.get("etag")
    if etag is None:
        try:
            _, etag = get_instance(subsystem, component, name)
        except InstanceNotFound as e:
            return {"error": str(e)}
    try:
        delete_instance(subsystem, component, name, expected_etag=etag)
    except InstanceNotFound as e:
        return {"error": str(e)}
    except SingletonNotInstanceable as e:
        return {"error": str(e)}
    return {"deleted": True, "name": name}


def handle_set_config(subsystem: str, name: str, payload: dict[str, Any]) -> Any:
    """Config 全置換。data.toml の top-level [name] を payload['data'] に差し替える。"""
    cfg = default_registry._configs.get((subsystem, name))
    if cfg is None:
        return {"error": f"config '{subsystem}.{name}' not found"}
    data_payload = payload.get("data")
    if not isinstance(data_payload, dict):
        return {"error": "data (object) required"}
    try:
        validated = cfg.model.model_validate(data_payload)
    except ValidationError as e:
        return {"error": f"validation_error: {e}"}
    new_value = validated.model_dump(exclude_none=True)
    path = subsystem_data_path(subsystem)
    data = read_toml(path)
    data[name] = new_value
    write_toml_atomic(path, data)
    return {"name": name, **new_value}


def handle_set_shared_spec(subsystem: str, component: str, payload: dict[str, Any]) -> Any:
    """MultiInstance の shared spec 全置換。"""
    spec = payload.get("spec")
    if not isinstance(spec, dict):
        return {"error": "spec (object) required"}
    etag = payload.get("etag")
    if etag is None:
        try:
            _, etag = get_shared_spec(subsystem, component)
        except InstanceNotFound:
            etag = None  # まだ spec が無い場合は etag 検査スキップ
        except SingletonNotInstanceable as e:
            return {"error": str(e)}
    try:
        new_spec, new_etag = set_shared_spec(subsystem, component, spec, expected_etag=etag)
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


def handle_analysis(subsystem: str | None, name: str, payload: dict[str, Any]) -> Any:
    """ad-hoc 関数を直接呼ぶ / veriq 経由なら evaluate して値を取り出す。"""
    adef = default_registry.analysis_or_none(subsystem, name)
    if adef is None:
        return {"error": f"analysis '{subsystem}.{name}' not found"}

    if adef.subsystem is None:
        import inspect

        sig = inspect.signature(adef.func)
        try:
            bound = sig.bind_partial(**payload)
            bound.apply_defaults()
        except TypeError as e:
            return {"error": f"argument error: {e}"}
        value = adef.func(*bound.args, **bound.kwargs)
        return {"value": _jsonable(value)}

    return _run_veriq_node(adef.subsystem, adef.name, verify=False)


def handle_verify_single(subsystem: str | None, name: str) -> Any:
    if subsystem is None:
        return {"error": "verify_* tools require veriq-attached analysis"}
    return _run_veriq_node(subsystem, name, verify=True)


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
                {"path": str(node.path), "value": _jsonable(node.value)}
                for node in tree.calculations
            ],
            "verifications": [
                {"path": str(node.path), "value": _jsonable(node.value)}
                for node in tree.verifications
            ],
        }
    out["scopes"] = scopes
    return out


def _run_veriq_node(subsystem: str, name: str, *, verify: bool) -> Any:
    import veriq as vq

    project = _build_project()
    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    tree = result.get_scope_tree(subsystem)
    if tree is None:
        return {"value": None}
    nodes = tree.verifications if verify else tree.calculations
    prefix = "?" if verify else "@"
    for node in nodes:
        if str(node.path).endswith(f"{prefix}{name}"):
            return {"value": _jsonable(node.value)}
    return {"value": None, "note": "node not found in evaluation result"}


def _build_project():
    import veriq as vq

    project = vq.Project("Craft")
    for sub in sorted(default_registry.subsystems()):
        mod = importlib.import_module(f"subsystems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is not None:
            project.add_scope(scope)
    return project


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)
