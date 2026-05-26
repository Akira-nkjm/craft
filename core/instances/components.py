"""Component インスタンス CRUD。

`systems/<sub>/data.toml` 上の Component インスタンスを読み書きする。

shared_spec=True (MultiInstance):
- TOML 上 `[<plural>.spec]` に共有 spec
- 各 instance は design / requirements / meta のみを保持
- GET 時は shared spec を instance に merge して view を返す
- POST/PUT/PATCH の payload に `spec` があれば、shared と一致する場合のみ受理。
  shared を更新したい場合は専用ヘルパ `set_shared_spec` を使う。
"""

from typing import Any

from pydantic import ValidationError

from core.paths import system_data_path
from core.toml_io import read_toml, write_toml_atomic
from schema import default_registry
from schema.registry import ComponentDefinition

from ._common import (
    InstanceAlreadyExists,
    InstanceNotFound,
    SharedSpecConflict,
    SingletonNotInstanceable,
    _check_etag,
    _deep_merge,
    _dig,
    _ensure_dig,
    _pop_dig,
    compute_etag,
)


def _component_defn(system: str, component: str) -> ComponentDefinition:
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        raise InstanceNotFound(f"Component '{system}.{component}' is not registered")
    return defn


def _instance_path(defn: ComponentDefinition, instance: str) -> list[str]:
    """instance 本体（design/requirements/meta）の TOML パス。"""
    if defn.cardinality == "multi":
        return [defn.plural, instance]
    return [defn.name]


def _shared_spec_path(defn: ComponentDefinition) -> list[str]:
    """shared spec の TOML パス（MultiInstance 専用）。"""
    return [defn.plural, "spec"]


def _instance_view(
    defn: ComponentDefinition, data: dict[str, Any], instance: str
) -> dict[str, Any] | None:
    """instance の dict を、shared spec を merge した形で返す。"""
    inst = _dig(data, _instance_path(defn, instance))
    if inst is None:
        return None
    if defn.cardinality != "multi":
        return inst
    view = dict(inst)
    if "spec" not in view:
        shared = _dig(data, _shared_spec_path(defn))
        if shared is not None:
            view["spec"] = dict(shared)
    return view


def _validate_entry(defn: ComponentDefinition, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        validated = defn.entry.model_validate(payload)
    except ValidationError:
        raise
    return validated.model_dump(exclude_none=True)


def _split_spec_and_rest(validated: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """validated dict を shared spec 候補 / instance 本体（spec 抜き）に分割。"""
    rest = {k: v for k, v in validated.items() if k != "spec"}
    return validated.get("spec", {}), rest


def _check_spec_matches_shared(
    defn: ComponentDefinition,
    data: dict[str, Any],
    spec_in_payload: dict[str, Any],
) -> None:
    """payload の spec が既存 shared と一致しているか確認。差異があれば例外。"""
    if not spec_in_payload:
        return
    shared = _dig(data, _shared_spec_path(defn))
    if shared is None:
        return  # まだ shared が無いので OK（呼び元が書き込む）
    if shared != spec_in_payload:
        raise SharedSpecConflict(
            f"payload.spec differs from shared spec at [{defn.plural}.spec]. "
            f"To update shared spec, use the dedicated endpoint."
        )


def get_instance(system: str, component: str, instance: str) -> tuple[dict[str, Any], str]:
    defn = _component_defn(system, component)
    data = read_toml(system_data_path(system))
    view = _instance_view(defn, data, instance)
    if view is None:
        raise InstanceNotFound(f"Instance '{system}.{component}.{instance}' not found in data.toml")
    return view, compute_etag(view)


def list_instances(system: str, component: str) -> dict[str, Any]:
    defn = _component_defn(system, component)
    data = read_toml(system_data_path(system))
    if defn.cardinality == "multi":
        section = _dig(data, [defn.plural]) or {}
        return {
            k: _instance_view(defn, data, k) or {}
            for k, v in section.items()
            if k != "spec" and isinstance(v, dict)
        }
    inst = _dig(data, _instance_path(defn, ""))
    return {defn.name: inst} if inst is not None else {}


def create_instance(
    system: str,
    component: str,
    instance: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    defn = _component_defn(system, component)
    if defn.cardinality != "multi":
        raise SingletonNotInstanceable(
            f"Singleton component '{system}.{component}' does not support instance creation"
        )

    data = read_toml(system_data_path(system))
    inst_keys = _instance_path(defn, instance)
    if _dig(data, inst_keys) is not None:
        raise InstanceAlreadyExists(f"Instance '{system}.{component}.{instance}' already exists")

    # shared_spec=True: payload に spec が無ければ既存 shared を補完して検証
    shared = _dig(data, _shared_spec_path(defn))
    enriched = dict(payload)
    if "spec" not in enriched and shared is not None:
        enriched["spec"] = dict(shared)

    validated = _validate_entry(defn, enriched)
    spec, rest = _split_spec_and_rest(validated)
    _check_spec_matches_shared(defn, data, spec)

    # shared spec が未設定なら、初回 instance の spec をプロモート
    if spec and shared is None:
        _ensure_dig(data, _shared_spec_path(defn)[:-1])[_shared_spec_path(defn)[-1]] = dict(spec)

    parent = _ensure_dig(data, inst_keys[:-1])
    parent[inst_keys[-1]] = rest
    write_toml_atomic(system_data_path(system), data)

    view = _instance_view(defn, data, instance) or rest
    return view, compute_etag(view)


def replace_instance(
    system: str,
    component: str,
    instance: str,
    payload: dict[str, Any],
    *,
    expected_etag: str | None,
) -> tuple[dict[str, Any], str]:
    defn = _component_defn(system, component)
    data = read_toml(system_data_path(system))
    inst_keys = _instance_path(defn, instance)
    current = _instance_view(defn, data, instance)
    if current is None:
        raise InstanceNotFound(f"Instance '{system}.{component}.{instance}' not found")
    _check_etag(current, expected_etag)

    enriched = dict(payload)
    if defn.cardinality == "multi" and "spec" not in enriched:
        shared = _dig(data, _shared_spec_path(defn))
        if shared is not None:
            enriched["spec"] = dict(shared)

    validated = _validate_entry(defn, enriched)
    if defn.cardinality == "multi":
        spec, rest = _split_spec_and_rest(validated)
        _check_spec_matches_shared(defn, data, spec)
        parent = _ensure_dig(data, inst_keys[:-1])
        parent[inst_keys[-1]] = rest
    else:
        parent = _ensure_dig(data, inst_keys[:-1])
        parent[inst_keys[-1]] = validated
    write_toml_atomic(system_data_path(system), data)

    view = _instance_view(defn, data, instance) or validated
    return view, compute_etag(view)


def patch_instance(
    system: str,
    component: str,
    instance: str,
    delta: dict[str, Any],
    *,
    expected_etag: str | None,
) -> tuple[dict[str, Any], str]:
    defn = _component_defn(system, component)
    data = read_toml(system_data_path(system))
    current = _instance_view(defn, data, instance)
    if current is None:
        raise InstanceNotFound(f"Instance '{system}.{component}.{instance}' not found")
    _check_etag(current, expected_etag)

    merged = _deep_merge(current, delta)
    validated = _validate_entry(defn, merged)

    inst_keys = _instance_path(defn, instance)
    if defn.cardinality == "multi":
        spec, rest = _split_spec_and_rest(validated)
        _check_spec_matches_shared(defn, data, spec)
        parent = _ensure_dig(data, inst_keys[:-1])
        parent[inst_keys[-1]] = rest
    else:
        parent = _ensure_dig(data, inst_keys[:-1])
        parent[inst_keys[-1]] = validated
    write_toml_atomic(system_data_path(system), data)

    view = _instance_view(defn, data, instance) or validated
    return view, compute_etag(view)


def delete_instance(
    system: str,
    component: str,
    instance: str,
    *,
    expected_etag: str | None,
) -> None:
    defn = _component_defn(system, component)
    if defn.cardinality != "multi":
        raise SingletonNotInstanceable(
            f"Singleton component '{system}.{component}' does not support deletion"
        )

    data = read_toml(system_data_path(system))
    inst_keys = _instance_path(defn, instance)
    current = _instance_view(defn, data, instance)
    if current is None:
        raise InstanceNotFound(f"Instance '{system}.{component}.{instance}' not found")
    _check_etag(current, expected_etag)

    _pop_dig(data, inst_keys)
    write_toml_atomic(system_data_path(system), data)


def get_shared_spec(system: str, component: str) -> tuple[dict[str, Any], str]:
    """MultiInstance の shared spec を取得。"""
    defn = _component_defn(system, component)
    if defn.cardinality != "multi":
        raise SingletonNotInstanceable(
            f"Component '{system}.{component}' is Singleton; no shared spec"
        )
    data = read_toml(system_data_path(system))
    shared = _dig(data, _shared_spec_path(defn))
    if shared is None:
        raise InstanceNotFound(f"Shared spec at [{defn.plural}.spec] not present yet")
    return shared, compute_etag(shared)


def set_shared_spec(
    system: str,
    component: str,
    spec_payload: dict[str, Any],
    *,
    expected_etag: str | None = None,
) -> tuple[dict[str, Any], str]:
    """shared spec を更新。ETag があれば検査。"""
    defn = _component_defn(system, component)
    if defn.cardinality != "multi":
        raise SingletonNotInstanceable(
            f"Component '{system}.{component}' is Singleton; no shared spec"
        )
    data = read_toml(system_data_path(system))
    keys = _shared_spec_path(defn)
    existing = _dig(data, keys)
    if existing is not None and expected_etag is not None:
        _check_etag(existing, expected_etag)
    try:
        validated = defn.spec.model_validate(spec_payload)
    except ValidationError:
        raise
    new_spec = validated.model_dump(exclude_none=True)
    parent = _ensure_dig(data, keys[:-1])
    parent[keys[-1]] = new_spec
    write_toml_atomic(system_data_path(system), data)
    return new_spec, compute_etag(new_spec)


def list_component_view(system: str, component: str) -> dict[str, Any]:
    """API / MCP 向け一覧 view。cardinality を問わず list_instances に委譲。"""
    return list_instances(system, component)


def get_component_view(
    system: str, component: str, instance: str | None
) -> tuple[dict[str, Any], str]:
    """API / MCP 向け単体 view。singleton は instance=None で呼ぶ。

    Raises InstanceNotFound if not found.
    """
    defn = _component_defn(system, component)
    resolved = instance if defn.cardinality == "multi" and instance is not None else ""
    data = read_toml(system_data_path(system))
    view = _instance_view(defn, data, resolved)
    if view is None:
        raise InstanceNotFound(f"Component '{system}.{component}' not found")
    return view, compute_etag(view)
