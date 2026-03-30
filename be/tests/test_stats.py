from httpx import AsyncClient

from tests.conftest import poll_job


async def test_stats_empty(app_client: AsyncClient) -> None:
    response = await app_client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_generations"] == 0
    assert body["avg_rating"] == 0.0
    assert body["avg_processing_time_ms"] == 0.0
    assert body["rating_distribution"] == {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}


async def test_stats_aggregation(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }

    r1 = await app_client.post("/overlay", files=files)
    assert r1.status_code == 202
    job_id_1 = r1.json()["job_id"]

    r2 = await app_client.post("/overlay", files=files)
    assert r2.status_code == 202
    job_id_2 = r2.json()["job_id"]

    await poll_job(app_client, job_id_1, "completed")
    await poll_job(app_client, job_id_2, "completed")

    await app_client.post(
        "/save",
        json={"job_id": job_id_1, "rating": 5, "processing_time_ms": 100},
    )
    await app_client.post(
        "/save",
        json={"job_id": job_id_2, "rating": 3, "processing_time_ms": 200},
    )

    response = await app_client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_generations"] == 2
    assert body["avg_rating"] == 4.0
    assert body["avg_processing_time_ms"] > 0
    assert body["rating_distribution"]["5"] == 1
    assert body["rating_distribution"]["3"] == 1
