"""POST /verify — veriq による検証を同期実行。

実行前に自動で `generated/merged.toml` を再生成し、それを veriq の入力とする。
"""

from fastapi import APIRouter

from api.errors import ConflictError, CraftAPIError, NotFoundError
from core.jobs import get_job, job_to_dict, submit_verify_job
from core.pipeline.merge import MergeConflict
from core.pipeline.verify import run_verify_core

router = APIRouter(prefix="/verify", tags=["verify"])


@router.post("")
def run_verify():
    try:
        return run_verify_core()
    except MergeConflict as e:
        raise ConflictError(f"merge failed: {e}") from e
    except Exception as e:
        raise CraftAPIError(f"veriq evaluation failed: {e}") from e


@router.post("/async")
async def run_verify_async():
    job = submit_verify_job()
    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{job_id}")
def get_verify_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise NotFoundError(f"Job '{job_id}' not found")
    return job_to_dict(job)
