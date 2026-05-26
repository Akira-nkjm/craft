"""POST /merge / GET /merged — TOML merge エンドポイント。"""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from core.merge import MERGED_TOML, MergeConflict, is_merge_stale, merge

router = APIRouter(tags=["merge"])


@router.post("/merge")
def run_merge(dry_run: bool = False) -> dict[str, Any]:
    try:
        result, _ = merge(dry_run=dry_run)
    except MergeConflict as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return {
        "output_path": str(result.output_path),
        "subsystems": list(result.subsystems),
        "source_files": result.source_files,
        "written": result.written,
        "stale": is_merge_stale(),
    }


@router.get("/merged")
def get_merged() -> Response:
    if not MERGED_TOML.exists():
        raise HTTPException(status_code=404, detail="merged.toml does not exist; POST /merge first")
    return Response(
        content=MERGED_TOML.read_bytes(),
        media_type="application/toml",
    )
