from fastapi import APIRouter

from src.models.analytics import StatsResponse
from src.services.analytics import analytics_store

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Return aggregated performance metrics across all generations."""
    return await analytics_store.stats()
