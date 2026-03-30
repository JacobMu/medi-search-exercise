import asyncio
import time
from concurrent.futures import ProcessPoolExecutor

from src.config import OUTPUT_DIR
from src.shared.analytics_store import analytics_store
from src.overlay.compositor import composite
from src.shared.job_store import job_store

# Shared process-pool — initialised once at import time so workers are
# forked before any large model/library state is loaded.
_executor = ProcessPoolExecutor()

# Holds strong references to background tasks so they are not garbage-collected
# before completion (per RUF006 / asyncio docs).
background_tasks: set[asyncio.Task[None]] = set()


async def run_composite_job(job_id: str, avatar_bytes: bytes, screenshot_bytes: bytes) -> None:
    """Background task: run compositing in a process-pool, update job state."""
    # Timer starts at task dispatch (includes job-store write + compositor work).
    start = time.monotonic()
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
    await analytics_store.record_completion(int((time.monotonic() - start) * 1000))
