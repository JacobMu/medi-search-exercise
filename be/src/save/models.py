from pydantic import BaseModel, Field


class SaveRequest(BaseModel):
    job_id: str = Field(..., max_length=128)
    rating: int = Field(..., ge=1, le=5)
    processing_time_ms: int = Field(..., ge=0)
