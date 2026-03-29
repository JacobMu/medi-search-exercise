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
    return data  # return last seen state


async def test_get_job_pending(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    r = await app_client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("pending", "processing")
    assert body["job_id"] == job_id


async def test_get_job_completed(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    data = await poll_job(app_client, job_id, "completed")
    assert data["status"] == "completed"
    assert "output_url" in data
    assert data["output_url"].endswith(".png")


async def test_get_job_not_found(app_client: AsyncClient) -> None:
    r = await app_client.get("/jobs/nonexistent-job-id-12345")
    assert r.status_code == 404


async def test_get_job_failed_graceful(app_client: AsyncClient, avatar_bytes: bytes) -> None:
    # WebP magic bytes pass validation but content is otherwise corrupt — compositor will fail
    corrupt_screenshot = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.webp", corrupt_screenshot, "image/webp"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    data = await poll_job(app_client, job_id, "failed")
    assert data["status"] == "failed"
