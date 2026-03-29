from httpx import AsyncClient


async def test_stats_empty(app_client: AsyncClient) -> None:
    response = await app_client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_generations"] == 0
    assert body["avg_rating"] == 0.0
    assert body["avg_processing_time_ms"] == 0.0
    assert body["rating_distribution"] == {}


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

    await app_client.post(
        "/save",
        json={"job_id": job_id_1, "rating": 5, "processing_time_ms": 200},
    )
    await app_client.post(
        "/save",
        json={"job_id": job_id_2, "rating": 3, "processing_time_ms": 400},
    )

    response = await app_client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_generations"] == 2
    assert body["avg_rating"] == 4.0
    assert body["avg_processing_time_ms"] == 300.0
    assert body["rating_distribution"]["5"] == 1
    assert body["rating_distribution"]["3"] == 1
