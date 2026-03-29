import asyncio
import time

from httpx import AsyncClient


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


async def test_full_user_journey(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    # 1. Upload images
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # 2. Poll until completed
    data = await poll_job(app_client, job_id, "completed")
    assert data["status"] == "completed"
    assert "output_url" in data
    assert data["output_url"].endswith(".png")

    # 3. Save feedback
    save_response = await app_client.post(
        "/save",
        json={"job_id": job_id, "rating": 5, "processing_time_ms": 1000},
    )
    assert save_response.status_code == 200
    assert save_response.json() == {"ok": True}

    # 4. Check stats
    stats_response = await app_client.get("/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_generations"] == 1
    assert stats["avg_rating"] == 5.0
    assert stats["rating_distribution"]["5"] == 1
