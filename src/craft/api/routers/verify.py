"""POST /verify — veriq による検証を同期実行。

入力は各 `systems/<name>/data.toml` を scope-input で直接ロードする
（`merged.toml` には依存しない。merge は別途 export 専用）。
"""

from fastapi import APIRouter

from craft.api.errors import CraftAPIError, NotFoundError
from craft.core.persistence.jobs import get_job, job_to_dict, submit_verify_job
from craft.core.pipeline.verify import run_verify_core

router = APIRouter(prefix="/verify", tags=["verify"])


@router.post("")
def run_verify():
    try:
        return run_verify_core()
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
