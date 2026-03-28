import asyncio
import uuid
from concurrent.futures import ProcessPoolExecutor
from typing import NotRequired, TypedDict

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from config import OUTPUT_DIR
from models.job import JobStatus
from services.compositor import composite
from store.jobs import job_store


class JobPayload(TypedDict):
    job_id: str
    status: JobStatus
    output_url: NotRequired[str]
    error: NotRequired[str]


router = APIRouter()

# Shared process-pool — initialised once at import time so workers are
# forked before any large model/library state is loaded.
_executor = ProcessPoolExecutor()

# Holds strong references to background tasks so they are not garbage-collected
# before completion (per RUF006 / asyncio docs).
_background_tasks: set[asyncio.Task[None]] = set()


async def _run_composite_job(job_id: str, avatar_bytes: bytes, screenshot_bytes: bytes) -> None:
    """Background task: run compositing in a process-pool, update job state."""
    await job_store.set_processing(job_id)
    loop = asyncio.get_running_loop()
    try:
        result_bytes: bytes = await loop.run_in_executor(
            _executor,
            composite,
            avatar_bytes,
            screenshot_bytes,
        )
    except Exception as exc:
        await job_store.set_failed(job_id, str(exc))
        return

    output_path = OUTPUT_DIR / f"{job_id}.png"
    output_path.write_bytes(result_bytes)

    await job_store.set_completed(job_id, str(output_path))


@router.post("/overlay", status_code=status.HTTP_202_ACCEPTED)
async def overlay(avatar: UploadFile, screenshot: UploadFile) -> JSONResponse:
    """Accept avatar + screenshot files and kick off async compositing."""
    avatar_bytes = await avatar.read()
    screenshot_bytes = await screenshot.read()

    if not avatar_bytes:
        raise HTTPException(status_code=400, detail="avatar file is empty.")
    if not screenshot_bytes:
        raise HTTPException(status_code=400, detail="screenshot file is empty.")

    job_id = str(uuid.uuid4())
    await job_store.create(job_id)

    task = asyncio.create_task(_run_composite_job(job_id, avatar_bytes, screenshot_bytes))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"job_id": job_id, "status": "pending"},
    )


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    """Poll job status and retrieve the output URL on completion."""
    record = await job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    payload: JobPayload = {"job_id": record.job_id, "status": record.status}
    if record.output_path:
        payload["output_url"] = f"/output/{record.job_id}.png"
    if record.error:
        payload["error"] = record.error
    return JSONResponse(content=payload)
