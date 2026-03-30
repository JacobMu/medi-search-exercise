from pydantic import BaseModel


class StatsResponse(BaseModel):
    total_generations: int
    avg_rating: float
    avg_processing_time_ms: float
    rating_distribution: dict[str, int]
