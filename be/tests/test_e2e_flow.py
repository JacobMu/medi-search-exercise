from unittest.mock import patch

from httpx import AsyncClient

from tests.conftest import poll_job


async def test_full_user_journey(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }


    overlay_response = await app_client.post("/overlay", files=files)
    job_id = overlay_response.json()["job_id"]
    job_data = await poll_job(app_client, job_id, "completed")
    save_response = await app_client.post(
        "/save",
        json={"job_id": job_id, "rating": 5, "processing_time_ms": 150},
    )
    stats_response = await app_client.get("/stats")

    assert overlay_response.status_code == 202
    assert job_data["status"] == "completed"
    assert "output_url" in job_data
    assert job_data["output_url"].endswith(".png")
    assert save_response.status_code == 200
    assert save_response.json() == {"ok": True}
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_generations"] == 1
    assert stats["avg_rating"] == 5.0
    assert stats["avg_processing_time_ms"] > 0
    assert stats["rating_distribution"]["5"] == 1


async def test_generation_without_rating_counted_in_stats(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }

    overlay_response = await app_client.post("/overlay", files=files)
    job_id = overlay_response.json()["job_id"]
    job_data = await poll_job(app_client, job_id, "completed")
    stats_response = await app_client.get("/stats")

    assert overlay_response.status_code == 202
    assert job_data["status"] == "completed"
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
        overlay_response = await app_client.post("/overlay", files=files)
        job_id = overlay_response.json()["job_id"]
        await poll_job(app_client, job_id, "failed")
    stats_response = await app_client.get("/stats")

    assert overlay_response.status_code == 202
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_generations"] == 0
    assert stats["avg_processing_time_ms"] == 0.0
