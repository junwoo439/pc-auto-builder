from __future__ import annotations

import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable


JobFunction = Callable[..., dict[str, object]]
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pc-import")
_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, object]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_job(
    job_id: str,
    function: JobFunction,
    kwargs: dict[str, object],
) -> None:
    with _LOCK:
        job = _JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = _now()

    try:
        result = function(**kwargs)
    except Exception as error:
        with _LOCK:
            job = _JOBS[job_id]
            job["status"] = "failed"
            job["finished_at"] = _now()
            job["error"] = str(error)
            job["traceback"] = traceback.format_exc(limit=8)
        return

    with _LOCK:
        job = _JOBS[job_id]
        job["status"] = "completed"
        job["finished_at"] = _now()
        job["result"] = result


def create_import_job(
    job_type: str,
    function: JobFunction,
    **kwargs: object,
) -> dict[str, object]:
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "queued",
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }

    with _LOCK:
        _JOBS[job_id] = job

    _EXECUTOR.submit(_run_job, job_id, function, kwargs)
    return dict(job)


def get_import_job(job_id: str) -> dict[str, object] | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return None

        public_job = dict(job)
        public_job.pop("traceback", None)
        return public_job
