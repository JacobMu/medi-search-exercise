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

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image

# Restrict maximum decoded image size to ~16 MP (4000x4000).
# PIL's default cap is ~178 MP; lowering it prevents excessive RAM
# allocation from oversized or crafted input images.
Image.MAX_IMAGE_PIXELS = 4000 * 4000

# Hue in OpenCV is 0-180; green sits roughly 35-85.
# Wide S/V ranges make detection robust to shadows and over-exposure.
_H_LOW, _H_HIGH = 40, 70
_S_LOW, _S_HIGH = 40, 255
_V_LOW, _V_HIGH = 40, 255


def get_image_from_bytes(image_bytes: bytes) -> cv2.typing.MatLike:
    image_pixels = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_pixels, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image. Please upload a valid image file.")
    return image


def get_contours_from_image(
    image: cv2.typing.MatLike,
) -> tuple[cv2.typing.MatLike, cv2.typing.MatLike]:
    avatar_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower: NDArray[np.uint8] = np.array([_H_LOW, _S_LOW, _V_LOW])
    upper: NDArray[np.uint8] = np.array([_H_HIGH, _S_HIGH, _V_HIGH])

    mask = cv2.inRange(avatar_hsv, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        image=mask_clean, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        raise ValueError(
            """
        No green-screen region detected in avatar.
        Please ensure the avatar has a clear green area for compositing.
        """
        )
    return max(contours, key=cv2.contourArea), mask_clean


def get_screen_bounding_box(
    screen_polygon_mask: cv2.typing.MatLike,
) -> cv2.typing.NumPyArrayFloat32:
    rect = cv2.minAreaRect(screen_polygon_mask)
    box = cv2.boxPoints(rect)

    four_corners = box.astype(np.float32)
    diagonal = four_corners.sum(axis=1)
    diagonal_mirror = np.diff(four_corners, axis=1).ravel()

    return np.array(
        [
            four_corners[np.argmin(diagonal)],
            four_corners[np.argmin(diagonal_mirror)],
            four_corners[np.argmax(diagonal)],
            four_corners[np.argmax(diagonal_mirror)],
        ],
        dtype=np.float32,
    )


def get_avatar_based_warped_screenshot(
    screenshot: cv2.typing.MatLike,
    screen_bounding_box: cv2.typing.NumPyArrayFloat32,
    avatar: cv2.typing.MatLike,
) -> cv2.typing.MatLike:
    screenshot_h, screenshot_w = screenshot.shape[:2]
    screenshot_corners = np.array(
        [[0, 0], [screenshot_w, 0], [screenshot_w, screenshot_h], [0, screenshot_h]],
        dtype=np.float32,
    )

    screenshot_mask = cv2.getPerspectiveTransform(screenshot_corners, screen_bounding_box)
    return cv2.warpPerspective(screenshot, screenshot_mask, (avatar.shape[1], avatar.shape[0]))


def get_soft_feathered_mask(composite_mask: cv2.typing.MatLike) -> cv2.typing.MatLike:
    mask_float = composite_mask.astype(np.float32) / 255.0
    mask_blurred = cv2.GaussianBlur(mask_float, (0, 0), sigmaX=2.5)
    alpha = mask_blurred[:, :, np.newaxis]  # (H, W, 1) for broadcasting over BGR
    return alpha


def composite(avatar_bytes: bytes, screenshot_bytes: bytes) -> bytes:
    """Composite screenshot onto the green-screen region of avatar.

    This is a pure, CPU-bound function — call it from a process-pool
    executor to keep the event loop free.

    Returns the composite image encoded as PNG bytes.
    Raises ValueError with a user-facing message on detection failure.
    """
    avatar = get_image_from_bytes(avatar_bytes)
    screenshot = get_image_from_bytes(screenshot_bytes)

    height, width = avatar.shape[:2]
    if height * width > Image.MAX_IMAGE_PIXELS:
        raise ValueError(
            "Avatar image is too large. Please upload an image smaller than 4000x4000 pixels."
        )
    screen_countour, screen_mask = get_contours_from_image(avatar)
    if cv2.contourArea(screen_countour) < 1000:
        raise ValueError(
            """
        Detected green-screen region is too small.
        Please ensure the avatar has a sufficiently large green area for compositing.
        """
        )
    screen_polygon_mask = cv2.convexHull(screen_countour)
    screen_bounding_box = get_screen_bounding_box(screen_polygon_mask)
    warped_screenshot = get_avatar_based_warped_screenshot(screenshot, screen_bounding_box, avatar)

    hull_fill = np.zeros(avatar.shape[:2], dtype=np.uint8)
    cv2.fillPoly(hull_fill, [screen_polygon_mask], 255)

    composite_mask = cv2.bitwise_and(screen_mask, hull_fill)
    alpha = get_soft_feathered_mask(composite_mask)
    result = (
        avatar.astype(np.float32) * (1.0 - alpha) + warped_screenshot.astype(np.float32) * alpha
    ).astype(np.uint8)
    _, buffer = cv2.imencode(".png", result)

    return buffer.tobytes()
