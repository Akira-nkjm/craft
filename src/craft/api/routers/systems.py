"""GET /systems — 登録済み system 名の一覧配信。"""

from fastapi import APIRouter

from craft.core.surface_ops.introspection import list_systems_summary

router = APIRouter(prefix="/systems", tags=["systems"])


@router.get("")
def list_systems() -> list[str]:
    return list_systems_summary()
