from unittest.mock import patch

from httpx import AsyncClient

from tests.conftest import poll_job


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
        json={"job_id": job_id, "rating": 5, "processing_time_ms": 150},
    )
    assert save_response.status_code == 200
    assert save_response.json() == {"ok": True}

    # 4. Check stats
    stats_response = await app_client.get("/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_generations"] == 1
    assert stats["avg_rating"] == 5.0
    assert stats["avg_processing_time_ms"] > 0
    assert stats["rating_distribution"]["5"] == 1


async def test_generation_without_rating_counted_in_stats(
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

    # 3. Check stats WITHOUT ever calling /save
    stats_response = await app_client.get("/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_generations"] == 1
    assert stats["avg_processing_time_ms"] > 0
    assert stats["avg_rating"] == 0.0
    assert stats["rating_distribution"] == {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}


async def test_failed_job_not_counted_in_stats(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    with patch("src.overlay.processing.composite", side_effect=RuntimeError("compositor failure")):
        response = await app_client.post("/overlay", files=files)
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        await poll_job(app_client, job_id, "failed")

    stats_response = await app_client.get("/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_generations"] == 0
    assert stats["avg_processing_time_ms"] == 0.0
