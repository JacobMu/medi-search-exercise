import os

from httpx import AsyncClient


async def test_overlay_success(
    app_client: AsyncClient, avatar_bytes: bytes, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] != ""
    assert body["status"] == "pending"


async def test_overlay_missing_avatar(app_client: AsyncClient, screenshot_bytes: bytes) -> None:
    files = {
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 422


async def test_overlay_missing_screenshot(app_client: AsyncClient, avatar_bytes: bytes) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 422


async def test_overlay_avatar_too_large(app_client: AsyncClient, screenshot_bytes: bytes) -> None:
    large_avatar = os.urandom(17 * 1024 * 1024)  # 17 MB
    files = {
        "avatar": ("avatar.png", large_avatar, "image/png"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 413


async def test_overlay_screenshot_too_large(app_client: AsyncClient, avatar_bytes: bytes) -> None:
    large_screenshot = os.urandom(17 * 1024 * 1024)  # 17 MB
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.png", large_screenshot, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 413


async def test_overlay_non_image_content_type(
    app_client: AsyncClient, screenshot_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.txt", b"not an image", "text/plain"),
        "screenshot": ("screenshot.png", screenshot_bytes, "image/png"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 415


async def test_overlay_non_image_content_type_screenshot(
    app_client: AsyncClient, avatar_bytes: bytes
) -> None:
    files = {
        "avatar": ("avatar.png", avatar_bytes, "image/png"),
        "screenshot": ("screenshot.txt", b"not an image", "text/plain"),
    }
    response = await app_client.post("/overlay", files=files)
    assert response.status_code == 415
