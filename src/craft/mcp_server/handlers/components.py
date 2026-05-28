"""Component MCP tool handlers."""

from typing import Any

from pydantic import ValidationError

from craft.core.errors import ETagMismatch, PreconditionRequired
from craft.core.instances import (
    InstanceNotFound,
    SingletonNotInstanceable,
    get_instance,
    get_shared_spec,
    list_instances,
    set_shared_spec,
)
from craft.core.io.toml_io import read_toml
from craft.core.paths import system_data_path
from craft.core.surface_ops.concurrency import ETagMode, resolve_expected_etag
from craft.core.surface_ops.operations import (
    create_component_op,
    delete_component_op,
    patch_component_op,
)
from craft.mcp_server.error_mapping import error_or_none
from craft.schema import default_registry


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
    """multi: name 必須 / singleton: name 不要。

    auto_etag=true 時のみ ETag を自動取得。
    """
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
