"""Components CRUD — TOML 上のインスタンス管理。

仕様: plan/Craft/01_仕様/API設計.md §Instances
ETag / If-Match による楽観的ロック。
"""

from typing import Any

from fastapi import APIRouter, Body, Header, Response

from api.error_mapping import raise_for_error, raise_for_result
from api.errors import NotFoundError
from core.instances import (
    InstanceNotFound,
    get_instance,
    list_instances,
)
from core.operations import (
    create_component_op,
    delete_component_op,
    patch_component_op,
    replace_component_op,
)
from core.paths import system_data_path
from core.toml_io import read_toml
from schema import default_registry

router = APIRouter(prefix="/components", tags=["components"])


@router.get("/{system}/{component}")
def list_component_instances(system: str, component: str) -> dict[str, Any]:
    defn = default_registry.component_or_none(system, component)
    if defn is None:
        raise NotFoundError(f"Component '{system}.{component}' is not registered")
    data = read_toml(system_data_path(system))
    if defn.cardinality == "multi":
        instances = list_instances(system, component)
    else:
        instances = data.get(defn.name, {})
    return {
        "system": system,
        "component": component,
        "plural": defn.plural,
        "cardinality": defn.cardinality,
        "instances": instances,
    }


@router.get("/{system}/{component}/{instance}")
def get_component_instance(
    system: str,
    component: str,
    instance: str,
    response: Response,
) -> dict[str, Any]:
    try:
        payload, etag = get_instance(system, component, instance)
    except InstanceNotFound as e:
        raise NotFoundError(str(e)) from e
    response.headers["ETag"] = etag
    return payload


@router.post("/{system}/{component}/{instance}", status_code=201)
def create_component_instance(
    system: str,
    component: str,
    instance: str,
    response: Response,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    result = create_component_op(system, component, instance, payload)
    return raise_for_result(result, response)


@router.put("/{system}/{component}/{instance}")
def replace_component_instance(
    system: str,
    component: str,
    instance: str,
    response: Response,
    payload: dict[str, Any] = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    result = replace_component_op(system, component, instance, payload, if_match=if_match)
    return raise_for_result(result, response)


@router.patch("/{system}/{component}/{instance}")
def patch_component_instance(
    system: str,
    component: str,
    instance: str,
    response: Response,
    delta: dict[str, Any] = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    result = patch_component_op(system, component, instance, delta, if_match=if_match)
    return raise_for_result(result, response)


@router.delete("/{system}/{component}/{instance}", status_code=204)
def delete_component_instance(
    system: str,
    component: str,
    instance: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> Response:
    result = delete_component_op(system, component, instance, if_match=if_match)
    raise_for_error(result)
    return Response(status_code=204)
