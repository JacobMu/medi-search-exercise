import asyncio
from datetime import UTC, datetime

from src.models.job import JobRecord, JobStatus


class JobStore:
    """Thread-safe in-memory job store backed by an asyncio.Lock.

    Architecture note: replace _store with a Redis/DB-backed
    implementation by subclassing or swapping this class.
    """

    def __init__(self) -> None:
        self._store: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, job_id: str) -> JobRecord:
        record = JobRecord(job_id=job_id)
        async with self._lock:
            self._store[job_id] = record
        return record

    async def get(self, job_id: str) -> JobRecord | None:
        async with self._lock:
            return self._store.get(job_id)

    async def _patch(self, job_id: str, **fields: object) -> None:
        """Update record fields and refresh updated_at under the lock."""
        async with self._lock:
            record = self._store[job_id]
            for attr, value in fields.items():
                setattr(record, attr, value)
            record.updated_at = datetime.now(tz=UTC)

    async def set_processing(self, job_id: str) -> None:
        await self._patch(job_id, status=JobStatus.PROCESSING)

    async def set_completed(self, job_id: str, output_path: str) -> None:
        await self._patch(job_id, status=JobStatus.COMPLETED, output_path=output_path)

    async def set_failed(self, job_id: str, error: str) -> None:
        await self._patch(job_id, status=JobStatus.FAILED, error=error)


# Module-level singleton — swap for a DI container when scaling.
job_store = JobStore()
