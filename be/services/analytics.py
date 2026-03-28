import asyncio
from collections import Counter

from models.analytics import SaveRequest, StatsResponse


class AnalyticsStore:
    """In-memory accumulator for generation analytics.

    Architecture note: persist entries to a time-series DB
    (e.g. TimescaleDB) by replacing _entries with DB writes.
    """

    def __init__(self) -> None:
        self._entries: list[SaveRequest] = []
        self._lock = asyncio.Lock()

    async def record(self, entry: SaveRequest) -> None:
        async with self._lock:
            self._entries.append(entry)

    async def stats(self) -> StatsResponse:
        async with self._lock:
            entries = list(self._entries)

        total = len(entries)
        if total == 0:
            return StatsResponse(
                total_generations=0,
                avg_rating=0.0,
                avg_processing_time_ms=0.0,
                rating_distribution={str(r): 0 for r in range(1, 6)},
            )

        avg_rating = sum(e.rating for e in entries) / total
        avg_processing_time_ms = sum(e.processing_time_ms for e in entries) / total

        distribution = {str(r): 0 for r in range(1, 6)}
        distribution.update(Counter(str(e.rating) for e in entries))

        return StatsResponse(
            total_generations=total,
            avg_rating=round(avg_rating, 2),
            avg_processing_time_ms=round(avg_processing_time_ms, 2),
            rating_distribution=distribution,
        )


analytics_store = AnalyticsStore()
