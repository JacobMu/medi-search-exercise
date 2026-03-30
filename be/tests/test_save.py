from httpx import AsyncClient


async def test_save_success(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    overlay_response = await app_client.post("/overlay", files=files)
    assert overlay_response.status_code == 202  # precondition
    job_id = overlay_response.json()["job_id"]

    response = await app_client.post(
        "/save",
        json={"job_id": job_id, "rating": 4, "processing_time_ms": 100},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


async def test_save_rating_too_low(app_client: AsyncClient) -> None:
    response = await app_client.post(
        "/save",
        json={"job_id": "any-id", "rating": 0},
    )

    assert response.status_code == 422


async def test_save_rating_too_high(app_client: AsyncClient) -> None:
    response = await app_client.post(
        "/save",
        json={"job_id": "any-id", "rating": 6},
    )

    assert response.status_code == 422


async def test_save_unknown_job_id(app_client: AsyncClient) -> None:
    response = await app_client.post(
        "/save",
        json={"job_id": "does-not-exist-xyz", "rating": 3, "processing_time_ms": 100},
    )

    assert response.status_code == 404
