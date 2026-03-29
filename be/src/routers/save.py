from fastapi import APIRouter, HTTPException

from src.models.analytics import SaveRequest
from src.services.analytics import analytics_store
from src.store.jobs import job_store

router = APIRouter()


@router.post("/save", status_code=200)
async def save(body: SaveRequest) -> dict[str, bool]:
    """Record a marketer's rating and processing time for analytics."""
    record = await job_store.get(body.job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{body.job_id}' not found.")

    await analytics_store.record(body)
    return {"ok": True}
