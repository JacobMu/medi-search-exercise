"""Image compositing service.

Pipeline:
1. Decode both images from raw bytes, normalising to solid RGB.
2. Convert the avatar to HSV colour space.
3. Build a binary mask for the green-screen region using a broad
   hue range that is robust to lighting variation.
4. Clean the mask with morphological ops, then find the largest
   contiguous green contour.
5. Approximate the contour to a 4-point convex hull (the phone
   screen quad).
6. Perspective-warp the screenshot into the screen quad using
   cv2.getPerspectiveTransform.
7. Alpha-blend the warped screenshot into the avatar using the
   refined mask.

All heavy work runs in a process-pool executor (called from the
router) so the asyncio event loop is never blocked.
"""

import io

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image

# Hue in OpenCV is 0-180; green sits roughly 35-85.
# Wide S/V ranges make detection robust to shadows and over-exposure.
_H_LOW, _H_HIGH = 35, 85
_S_LOW, _S_HIGH = 40, 255
_V_LOW, _V_HIGH = 40, 255

_ERODE_KERNEL = np.ones((5, 5), np.uint8)
_DILATE_KERNEL = np.ones((7, 7), np.uint8)


def _bytes_to_rgb_array(data: bytes) -> NDArray[np.uint8]:
    """Decode image bytes to a solid RGB NumPy array (HxWx3, uint8).

    Handles PNG/JPEG/WebP, RGBA, LA, P palette modes, etc.
    """
    img = Image.open(io.BytesIO(data))
    # LA needs to be normalised to RGBA so the alpha-compositing branch handles both.
    if img.mode == "LA":
        img = img.convert("RGBA")
    match img.mode:
        case "RGBA":
            # Flatten transparency onto white to avoid artefacts.
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        case "RGB":
            pass
        case _:
            img = img.convert("RGB")
    return np.array(img, dtype=np.uint8)


def _build_green_mask(avatar_bgr: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Return a cleaned binary mask for the green-screen region."""
    hsv = cv2.cvtColor(avatar_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([_H_LOW, _S_LOW, _V_LOW], dtype=np.uint8)
    upper = np.array([_H_HIGH, _S_HIGH, _V_HIGH], dtype=np.uint8)
    raw_mask = cv2.inRange(hsv, lower, upper)
    # Erode first to eliminate noise at edges, then dilate to fill holes.
    mask = cv2.erode(raw_mask, _ERODE_KERNEL, iterations=2)
    mask = cv2.dilate(mask, _DILATE_KERNEL, iterations=2)
    return mask.astype(np.uint8)


def _find_screen_quad(mask: NDArray[np.uint8]) -> NDArray[np.float32]:
    """Return the 4-corner convex hull of the largest green contour.

    Returns an array of shape (4, 2) in float32.
    Raises ValueError if no suitable contour is found.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No green-screen region detected in the avatar image.")

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 500:
        raise ValueError("Green-screen region is too small to be a phone screen.")

    hull = cv2.convexHull(largest)
    epsilon = 0.02 * cv2.arcLength(hull, closed=True)
    approx = cv2.approxPolyDP(hull, epsilon, closed=True)

    # If approximation doesn't yield exactly 4 points, fall back to the
    # bounding rotated rectangle's corners.
    if len(approx) != 4:
        rect = cv2.minAreaRect(largest)
        approx = cv2.boxPoints(rect).reshape(-1, 1, 2)

    pts = approx.reshape(-1, 2).astype(np.float32)

    coord_sums = pts.sum(axis=1)
    coord_diffs = np.diff(pts, axis=1).flatten()
    ordered = np.array(
        [
            pts[np.argmin(coord_sums)],  # top-left
            pts[np.argmin(coord_diffs)],  # top-right
            pts[np.argmax(coord_sums)],  # bottom-right
            pts[np.argmax(coord_diffs)],  # bottom-left
        ],
        dtype=np.float32,
    )
    return ordered


def _warp_screenshot(
    screenshot_bgr: NDArray[np.uint8],
    dst_pts: NDArray[np.float32],
    canvas_shape: tuple[int, int],
) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    """Perspective-warp the screenshot to fill dst_pts on a blank canvas.

    Returns (warped_image, warp_mask) — both HxW arrays / HxWx3 arrays.
    """
    h, w = screenshot_bgr.shape[:2]
    src_pts = np.array(
        [[0, 0], [w, 0], [w, h], [0, h]],
        dtype=np.float32,
    )
    m = cv2.getPerspectiveTransform(src_pts, dst_pts)
    canvas_h, canvas_w = canvas_shape
    warped = cv2.warpPerspective(screenshot_bgr, m, (canvas_w, canvas_h))

    src_mask = np.ones((h, w), dtype=np.uint8) * 255
    warp_mask = cv2.warpPerspective(src_mask, m, (canvas_w, canvas_h))
    return warped.astype(np.uint8), warp_mask.astype(np.uint8)


def composite(avatar_bytes: bytes, screenshot_bytes: bytes) -> bytes:
    """Composite screenshot onto the green-screen region of avatar.

    This is a pure, CPU-bound function — call it from a process-pool
    executor to keep the event loop free.

    Returns the composite image encoded as PNG bytes.
    Raises ValueError with a user-facing message on detection failure.
    """
    avatar_rgb = _bytes_to_rgb_array(avatar_bytes)
    screenshot_rgb = _bytes_to_rgb_array(screenshot_bytes)

    # Work in BGR throughout (OpenCV native format).
    avatar_bgr = cv2.cvtColor(avatar_rgb, cv2.COLOR_RGB2BGR).astype(np.uint8)
    screenshot_bgr = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2BGR).astype(np.uint8)

    mask = _build_green_mask(avatar_bgr)
    screen_quad = _find_screen_quad(mask)

    canvas_h, canvas_w = avatar_bgr.shape[:2]
    warped, warp_mask = _warp_screenshot(screenshot_bgr, screen_quad, (canvas_h, canvas_w))

    result = avatar_bgr.copy()
    result[warp_mask > 0] = warped[warp_mask > 0]

    success, encoded = cv2.imencode(".png", result)
    if not success:
        raise RuntimeError("Failed to encode composite image.")

    return encoded.tobytes()
