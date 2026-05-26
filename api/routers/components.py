"""Components CRUD — TOML 上のインスタンス管理。

仕様: plan/Craft/01_仕様/API設計.md §Instances
ETag / If-Match による楽観的ロック。
"""

from typing import Any

from fastapi import APIRouter, Body, Header, Response

from api.errors import ConflictError, NotFoundError
from core.instances import (
    InstanceAlreadyExists,
    InstanceNotFound,
    SharedSpecConflict,
    SingletonNotInstanceable,
    create_instance,
    delete_instance,
    get_instance,
    list_instances,
    patch_instance,
    replace_instance,
)
from core.paths import subsystem_data_path
from core.toml_io import read_toml
from schema import default_registry

router = APIRouter(prefix="/components", tags=["components"])


@router.get("/{subsystem}/{component}")
def list_component_instances(subsystem: str, component: str) -> dict[str, Any]:
    defn = default_registry.component_or_none(subsystem, component)
    if defn is None:
        raise NotFoundError(f"Component '{subsystem}.{component}' is not registered")
    data = read_toml(subsystem_data_path(subsystem))
    if defn.cardinality == "multi":
        instances = list_instances(subsystem, component)
    else:
        instances = data.get(defn.name, {})
    return {
        "subsystem": subsystem,
        "component": component,
        "plural": defn.plural,
        "cardinality": defn.cardinality,
        "instances": instances,
    }


@router.get("/{subsystem}/{component}/{instance}")
def get_component_instance(
    subsystem: str,
    component: str,
    instance: str,
    response: Response,
) -> dict[str, Any]:
    try:
        payload, etag = get_instance(subsystem, component, instance)
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    response.headers["ETag"] = etag
    return payload


@router.post("/{subsystem}/{component}/{instance}", status_code=201)
def create_component_instance(
    subsystem: str,
    component: str,
    instance: str,
    response: Response,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        created, etag = create_instance(subsystem, component, instance, payload)
    except InstanceAlreadyExists as e:
        raise ConflictError(str(e)) from e
    except SingletonNotInstanceable as e:
        raise ConflictError(str(e)) from e
    except SharedSpecConflict as e:
        raise ConflictError(str(e)) from e
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    response.headers["ETag"] = etag
    return created


@router.put("/{subsystem}/{component}/{instance}")
def replace_component_instance(
    subsystem: str,
    component: str,
    instance: str,
    response: Response,
    payload: dict[str, Any] = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    try:
        updated, etag = replace_instance(
            subsystem, component, instance, payload, expected_etag=if_match
        )
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    except SharedSpecConflict as e:
        raise ConflictError(str(e)) from e
    response.headers["ETag"] = etag
    return updated


@router.patch("/{subsystem}/{component}/{instance}")
def patch_component_instance(
    subsystem: str,
    component: str,
    instance: str,
    response: Response,
    delta: dict[str, Any] = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    try:
        updated, etag = patch_instance(
            subsystem, component, instance, delta, expected_etag=if_match
        )
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    except SharedSpecConflict as e:
        raise ConflictError(str(e)) from e
    response.headers["ETag"] = etag
    return updated


@router.delete("/{subsystem}/{component}/{instance}", status_code=204)
def delete_component_instance(
    subsystem: str,
    component: str,
    instance: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> Response:
    try:
        delete_instance(subsystem, component, instance, expected_etag=if_match)
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    except SingletonNotInstanceable as e:
        raise ConflictError(str(e)) from e
    return Response(status_code=204)
