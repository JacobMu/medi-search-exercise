import asyncio
import uuid
from typing import NotRequired, TypedDict

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from src.config import MAX_IMAGE_BYTES
from src.models.job import JobStatus
from src.overlay.file_utils import read_limited
from src.overlay.processing import background_tasks, run_composite_job
from src.store.jobs import job_store


class JobPayload(TypedDict):
    job_id: str
    status: JobStatus
    output_url: NotRequired[str]
    error: NotRequired[str]


_ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}

_MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/webp": (b"RIFF",),  # also checks bytes 8-11 below
}


def _check_magic_bytes(content_type: str, data: bytes, field: str) -> None:
    """Raise 415 if *data* does not match the declared *content_type* magic bytes."""
    header = data[:12]
    if content_type == "image/png":
        valid = header[:8] == b"\x89PNG\r\n\x1a\n"
    elif content_type == "image/jpeg":
        valid = header[:3] == b"\xff\xd8\xff"
    elif content_type == "image/webp":
        valid = header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    else:
        valid = False
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"'{field}' magic bytes do not match declared content type '{content_type}'.",
        )


router = APIRouter()


@router.post("/overlay", status_code=status.HTTP_202_ACCEPTED)
async def overlay(avatar: UploadFile, screenshot: UploadFile) -> JSONResponse:
    """Accept avatar + screenshot files and kick off async compositing."""
    for field, upload in (("avatar", avatar), ("screenshot", screenshot)):
        if upload.content_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"'{field}' must be one of: {', '.join(sorted(_ALLOWED_MIME_TYPES))}.",
            )

    avatar_bytes = await read_limited(avatar, MAX_IMAGE_BYTES, "avatar")
    screenshot_bytes = await read_limited(screenshot, MAX_IMAGE_BYTES, "screenshot")

    if not avatar_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="avatar file is empty.")
    if not screenshot_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="screenshot file is empty."
        )

    _check_magic_bytes(avatar.content_type, avatar_bytes, "avatar")
    _check_magic_bytes(screenshot.content_type, screenshot_bytes, "screenshot")

    job_id = str(uuid.uuid4())
    await job_store.create(job_id)

    task = asyncio.create_task(run_composite_job(job_id, avatar_bytes, screenshot_bytes))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
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
