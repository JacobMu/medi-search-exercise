import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from src.services.analytics import analytics_store
from src.store.jobs import job_store

TEST_ASSETS = Path(__file__).parent.parent.parent / "test_assets"


async def poll_job(
    client: AsyncClient,
    job_id: str,
    target_status: str,
    timeout: float = 15.0,
    interval: float = 0.5,
) -> dict:
    deadline = time.monotonic() + timeout
    data: dict = {}
    while time.monotonic() < deadline:
        r = await client.get(f"/jobs/{job_id}")
        r.raise_for_status()
        data = r.json()
        if data["status"] == target_status:
            return data
        await asyncio.sleep(interval)
    return data


@pytest.fixture
async def app_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def reset_stores() -> None:
    job_store._store.clear()
    analytics_store._entries.clear()
    analytics_store._completions.clear()


@pytest.fixture
def avatar_bytes() -> bytes:
    return (TEST_ASSETS / "avatar1.png").read_bytes()


@pytest.fixture
def screenshot_bytes() -> bytes:
    return (TEST_ASSETS / "screenshot.png").read_bytes()
