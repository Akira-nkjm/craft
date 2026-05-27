"""Config インスタンス CRUD。

`systems/<sub>/data.toml` 上の Config エントリを読み書きする。
"""

from typing import Any

from pydantic import ValidationError

from core.io.toml_io import read_toml, write_toml_atomic
from core.paths import system_data_path
from schema import default_registry
from schema.registry import ConfigDefinition

from ._common import (
    InstanceNotFound,
    SingletonNotInstanceable,
    _check_etag,
    _deep_merge,
    _dig,
    _ensure_dig,
    _pop_dig,
    compute_etag,
)


def _config_defn(system: str, config: str) -> ConfigDefinition:
    defn = default_registry._configs.get((system, config))
    if defn is None:
        raise InstanceNotFound(f"Config '{system}.{config}' is not registered")
    return defn


def get_singleton_config(system: str, config: str) -> tuple[dict[str, Any], str]:
    """Singleton config を取得。"""
    defn = _config_defn(system, config)
    data = read_toml(system_data_path(system))
    entry = _dig(data, [defn.name]) or {}
    return entry, compute_etag(entry)


def set_singleton_config(
    system: str,
    config: str,
    payload: dict[str, Any],
    *,
    expected_etag: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Singleton config を全置換。"""
    defn = _config_defn(system, config)
    if defn.cardinality != "single":
        raise SingletonNotInstanceable(
            f"Config '{system}.{config}' is MultiInstance; use set/patch config instance"
        )
    try:
        validated = defn.model.model_validate(payload)
    except ValidationError:
        raise
    new_value = validated.model_dump(exclude_none=True)
    data = read_toml(system_data_path(system))
    existing = _dig(data, [defn.name])
    if existing is not None and expected_etag is not None:
        _check_etag(existing, expected_etag)
    data[defn.name] = new_value
    write_toml_atomic(system_data_path(system), data)
    return new_value, compute_etag(new_value)


def list_config_instances(system: str, config: str) -> dict[str, Any]:
    """MultiInstance config の全エントリを返す。"""
    defn = _config_defn(system, config)
    data = read_toml(system_data_path(system))
    section = _dig(data, [defn.plural]) or {}
    return {k: v for k, v in section.items() if isinstance(v, dict)}


def get_config_instance(system: str, config: str, key: str) -> tuple[dict[str, Any], str]:
    """MultiInstance config の1エントリを取得。"""
    defn = _config_defn(system, config)
    data = read_toml(system_data_path(system))
    entry = _dig(data, [defn.plural, key])
    if entry is None:
        raise InstanceNotFound(f"Config entry '{system}.{config}.{key}' not found")
    return entry, compute_etag(entry)


def set_config_instance(
    system: str,
    config: str,
    key: str,
    payload: dict[str, Any],
    *,
    expected_etag: str | None = None,
) -> tuple[dict[str, Any], str]:
    """MultiInstance config エントリを作成または全置換。"""
    defn = _config_defn(system, config)
    if defn.cardinality != "multi":
        raise SingletonNotInstanceable(
            f"Singleton config '{system}.{config}' does not support instance keys"
        )
    try:
        validated = defn.model.model_validate(payload)
    except ValidationError:
        raise
    new_value = validated.model_dump(exclude_none=True)
    data = read_toml(system_data_path(system))
    existing = _dig(data, [defn.plural, key])
    if existing is not None and expected_etag is not None:
        _check_etag(existing, expected_etag)
    parent = _ensure_dig(data, [defn.plural])
    parent[key] = new_value
    write_toml_atomic(system_data_path(system), data)
    return new_value, compute_etag(new_value)


def patch_config_instance(
    system: str,
    config: str,
    key: str,
    delta: dict[str, Any],
    *,
    expected_etag: str | None,
) -> tuple[dict[str, Any], str]:
    """MultiInstance config エントリを部分更新。"""
    defn = _config_defn(system, config)
    data = read_toml(system_data_path(system))
    current = _dig(data, [defn.plural, key])
    if current is None:
        raise InstanceNotFound(f"Config entry '{system}.{config}.{key}' not found")
    _check_etag(current, expected_etag)
    merged = _deep_merge(current, delta)
    try:
        validated = defn.model.model_validate(merged)
    except ValidationError:
        raise
    new_value = validated.model_dump(exclude_none=True)
    parent = _ensure_dig(data, [defn.plural])
    parent[key] = new_value
    write_toml_atomic(system_data_path(system), data)
    return new_value, compute_etag(new_value)


def delete_config_instance(
    system: str,
    config: str,
    key: str,
    *,
    expected_etag: str | None,
) -> None:
    """MultiInstance config エントリを削除。"""
    defn = _config_defn(system, config)
    if defn.cardinality != "multi":
        raise SingletonNotInstanceable(
            f"Singleton config '{system}.{config}' does not support deletion"
        )
    data = read_toml(system_data_path(system))
    current = _dig(data, [defn.plural, key])
    if current is None:
        raise InstanceNotFound(f"Config entry '{system}.{config}.{key}' not found")
    _check_etag(current, expected_etag)
    _pop_dig(data, [defn.plural, key])
    write_toml_atomic(system_data_path(system), data)
