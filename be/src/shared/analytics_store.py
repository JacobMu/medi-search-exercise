import asyncio
from collections import Counter

from src.save.models import SaveRequest
from src.stats.models import StatsResponse


class AnalyticsStore:
    """In-memory accumulator for generation analytics.

    Architecture note: persist entries to a time-series DB
    (e.g. TimescaleDB) by replacing _entries with DB writes.
    """

    def __init__(self) -> None:
        self._entries: list[SaveRequest] = []
        self._completions: list[int] = []
        self._lock = asyncio.Lock()

    async def record(self, entry: SaveRequest) -> None:
        async with self._lock:
            self._entries.append(entry)

    async def record_completion(self, processing_time_ms: int) -> None:
        async with self._lock:
            self._completions.append(processing_time_ms)

    async def stats(self) -> StatsResponse:
        async with self._lock:
            entries = list(self._entries)
            completions = list(self._completions)

        total = len(completions)
        if total == 0:
            return StatsResponse(
                total_generations=0,
                avg_rating=0.0,
                avg_processing_time_ms=0.0,
                rating_distribution={},
            )

        avg_processing_time_ms = sum(completions) / total

        rated = len(entries)
        if rated == 0:
            avg_rating = 0.0
            distribution: dict[str, int] = {}
        else:
            avg_rating = sum(e.rating for e in entries) / rated
            distribution = dict(Counter(str(e.rating) for e in entries))

        return StatsResponse(
            total_generations=total,
            avg_rating=round(avg_rating, 2),
            avg_processing_time_ms=round(avg_processing_time_ms, 2),
            rating_distribution=distribution,
        )


analytics_store = AnalyticsStore()
