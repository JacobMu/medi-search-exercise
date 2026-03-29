from pydantic import BaseModel, Field


class SaveRequest(BaseModel):
    job_id: str
    rating: int = Field(..., ge=1, le=5)
    processing_time_ms: int = Field(..., ge=0)


class StatsResponse(BaseModel):
    total_generations: int
    avg_rating: float
    avg_processing_time_ms: float
    rating_distribution: dict[str, int]
