"""File-backed background jobs."""

import asyncio
import contextlib
import importlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.verify import run_verify_core

merge_mod = importlib.import_module("core.merge")


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    status: str
    kind: str
    started_at: str | None
    finished_at: str | None
    result: dict[str, Any] | None
    error: str | None


def jobs_dir() -> Path:
    return merge_mod.GENERATED_DIR / "runs" / "jobs"


def submit_verify_job() -> Job:
    job = Job(
        id=_new_job_id(),
        status="queued",
        kind="verify",
        started_at=None,
        finished_at=None,
        result=None,
        error=None,
    )
    _write_job(job)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        loop.create_task(_run_verify_job(job.id))
    return job


def get_job(job_id: str) -> Job | None:
    path = jobs_dir() / f"{job_id}.json"
    if not path.exists():
        return None
    return _job_from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_jobs() -> list[Job]:
    if not jobs_dir().exists():
        return []
    jobs = [get_job(p.stem) for p in sorted(jobs_dir().glob("*.json"), reverse=True)]
    return [job for job in jobs if job is not None]


def job_to_dict(job: Job) -> dict[str, Any]:
    return asdict(job)


async def _run_verify_job(job_id: str) -> None:
    started = _now()
    _write_job(
        Job(
            id=job_id,
            status="running",
            kind="verify",
            started_at=started,
            finished_at=None,
            result=None,
            error=None,
        )
    )
    try:
        result = await asyncio.to_thread(run_verify_core)
    except Exception as exc:
        _write_job(
            Job(
                id=job_id,
                status="failure",
                kind="verify",
                started_at=started,
                finished_at=_now(),
                result=None,
                error=str(exc),
            )
        )
        return
    _write_job(
        Job(
            id=job_id,
            status="success",
            kind="verify",
            started_at=started,
            finished_at=_now(),
            result=result,
            error=None,
        )
    )


def _new_job_id() -> str:
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"{stamp}-{os.urandom(3).hex()}"


def _now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def _write_job(job: Job) -> None:
    directory = jobs_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{job.id}.json"
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(job), f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def _job_from_dict(payload: dict[str, Any]) -> Job:
    return Job(
        id=str(payload["id"]),
        status=str(payload["status"]),
        kind=str(payload["kind"]),
        started_at=payload.get("started_at"),
        finished_at=payload.get("finished_at"),
        result=payload.get("result"),
        error=payload.get("error"),
    )
