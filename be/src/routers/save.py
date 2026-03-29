from fastapi import APIRouter, HTTPException, status

from src.models.analytics import SaveRequest
from src.services.analytics import analytics_store
from src.store.jobs import job_store

router = APIRouter()


@router.post("/save", status_code=200)
async def save(body: SaveRequest) -> dict[str, bool]:
    """Record a marketer's rating and processing time for analytics."""
    record = await job_store.get(body.job_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    await analytics_store.record(body)
    return {"ok": True}
