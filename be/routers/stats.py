from fastapi import APIRouter

from models.analytics import StatsResponse
from services.analytics import analytics_store

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Return aggregated performance metrics across all generations."""
    return await analytics_store.stats()
