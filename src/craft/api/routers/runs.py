"""Verification run history API."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response

from craft.api.errors import NotFoundError
from craft.core.persistence.jobs import get_job, job_to_dict
from craft.core.persistence.runs import (
    get_run,
    get_run_artifact,
    latest_run_id,
    list_runs,
    run_to_dict,
)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs_endpoint(limit: int = 20) -> dict[str, Any]:
    return {"runs": [run_to_dict(run) for run in list_runs(limit=limit)]}


@router.get("/latest")
def get_latest_run() -> dict[str, Any]:
    run_id = latest_run_id()
    if run_id is None:
        raise NotFoundError("No verification runs found")
    run = get_run(run_id)
    if run is None:
        raise NotFoundError(f"Run '{run_id}' not found")
    return run_to_dict(run)


@router.get("/{run_id}")
def get_run_endpoint(run_id: str) -> dict[str, Any]:
    run = get_run(run_id)
    if run is not None:
        return run_to_dict(run)
    job = get_job(run_id)
    if job is not None:
        return job_to_dict(job)
    raise NotFoundError(f"Run '{run_id}' not found")


@router.get("/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str) -> Response:
    allowed = {"result.toml", "input.toml", "meta.json", "trace.json"}
    if name not in allowed:
        raise NotFoundError(f"Artifact '{name}' not found")
    content = get_run_artifact(run_id, name)
    if content is None:
        raise NotFoundError(f"Artifact '{name}' not found")
    return Response(content=content, media_type=_media_type(name))


def _media_type(name: str) -> str:
    if name.endswith(".json"):
        return "application/json"
    if name.endswith(".toml"):
        return "application/toml"
    return "application/octet-stream"
