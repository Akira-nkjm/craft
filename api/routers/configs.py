"""Configs CRUD — Singleton / MultiInstance config の読み書き。

Singleton: GET /configs/{system}/{config}
           PUT /configs/{system}/{config}
Multi:     GET /configs/{system}/{config}          → 全エントリ一覧
           GET /configs/{system}/{config}/{key}    → 1エントリ取得
           PUT /configs/{system}/{config}/{key}    → 作成 or 全置換
           PATCH /configs/{system}/{config}/{key}  → 部分更新
           DELETE /configs/{system}/{config}/{key} → 削除
"""

from typing import Any

from fastapi import APIRouter, Body, Header, Response

from api.error_mapping import raise_for_error, raise_for_result
from api.errors import NotFoundError
from core.instances import (
    InstanceNotFound,
    get_config_instance,
    get_singleton_config,
    list_config_instances,
)
from core.surface_ops.operations import (
    delete_config_entry_op,
    patch_config_entry_op,
    set_config_entry_op,
    set_singleton_config_op,
)
from schema import default_registry

router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("/{system}/{config}")
def get_config(system: str, config: str, response: Response) -> dict[str, Any]:
    defn = default_registry._configs.get((system, config))
    if defn is None:
        raise NotFoundError(f"Config '{system}.{config}' not found in registry")
    if defn.cardinality == "multi":
        return {
            "system": system,
            "config": config,
            "plural": defn.plural,
            "cardinality": "multi",
            "instances": list_config_instances(system, config),
        }
    payload, etag = get_singleton_config(system, config)
    response.headers["ETag"] = etag
    return payload


@router.put("/{system}/{config}")
def set_config(
    system: str,
    config: str,
    response: Response,
    payload: dict[str, Any] = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    defn = default_registry._configs.get((system, config))
    if defn is None:
        raise NotFoundError(f"Config '{system}.{config}' not found in registry")
    result = set_singleton_config_op(system, config, payload, if_match=if_match)
    return raise_for_result(result, response)


@router.get("/{system}/{config}/{key}")
def get_config_entry(system: str, config: str, key: str, response: Response) -> dict[str, Any]:
    try:
        payload, etag = get_config_instance(system, config, key)
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    response.headers["ETag"] = etag
    return payload


@router.put("/{system}/{config}/{key}")
def set_config_entry(
    system: str,
    config: str,
    key: str,
    response: Response,
    payload: dict[str, Any] = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    result = set_config_entry_op(system, config, key, payload, if_match=if_match)
    return raise_for_result(result, response)


@router.patch("/{system}/{config}/{key}")
def patch_config_entry(
    system: str,
    config: str,
    key: str,
    response: Response,
    delta: dict[str, Any] = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    result = patch_config_entry_op(system, config, key, delta, if_match=if_match)
    return raise_for_result(result, response)


@router.delete("/{system}/{config}/{key}", status_code=204)
def delete_config_entry(
    system: str,
    config: str,
    key: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> Response:
    result = delete_config_entry_op(system, config, key, if_match=if_match)
    raise_for_error(result)
    return Response(status_code=204)
