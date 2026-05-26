"""POST /scaffold — registry → data.toml 雛形生成 (add-missing)。"""

from typing import Any

from fastapi import APIRouter, HTTPException

from core.scaffold import scaffold_all, scaffold_subsystem

router = APIRouter(prefix="/scaffold", tags=["scaffold"])


def _serialize(result: Any) -> dict[str, Any]:
    return {
        "subsystem": result.subsystem,
        "file_path": str(result.file_path),
        "written": result.written,
        "added_paths": list(result.added_paths),
        "removed_warnings": list(result.removed_warnings),
    }


@router.post("")
def run_scaffold_all(dry_run: bool = False) -> dict[str, Any]:
    results = scaffold_all(dry_run=dry_run)
    return {"results": [_serialize(r) for r in results]}


@router.post("/{subsystem}")
def run_scaffold_subsystem(subsystem: str, dry_run: bool = False) -> dict[str, Any]:
    try:
        result, _ = scaffold_subsystem(subsystem, dry_run=dry_run)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _serialize(result)


@router.get("/preview/{subsystem}")
def preview_scaffold(subsystem: str) -> dict[str, Any]:
    try:
        result, data = scaffold_subsystem(subsystem, dry_run=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {
        "subsystem": subsystem,
        "added_paths": list(result.added_paths),
        "removed_warnings": list(result.removed_warnings),
        "data_preview": data,
    }
