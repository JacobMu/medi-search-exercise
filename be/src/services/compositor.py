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

# Restrict maximum decoded image size to ~16 MP (4000x4000).
# PIL's default cap is ~178 MP; lowering it prevents excessive RAM
# allocation from oversized or crafted input images.
Image.MAX_IMAGE_PIXELS = 4000 * 4000

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


def _inset_quad(pts: NDArray[np.float32], pixels: int = 10) -> NDArray[np.float32]:
    """Shrink a 4-point quad by moving each edge inward by `pixels`.

    Translates each edge inward perpendicular to itself, then recomputes corners
    as intersections of adjacent inset edges.  This gives a uniform inset on all
    sides regardless of the quad's aspect ratio.  The previous corner-toward-
    centroid approach over-shrank the longer axis (vertical for portrait phones),
    leaving the top/bottom edges under-covered while the shorter axis was
    under-inset, causing overflow on those sides.
    """
    n = 4
    centroid = pts.mean(axis=0).astype(np.float64)
    inset_lines: list[tuple[NDArray[np.float64], NDArray[np.float64]]] = []

    for i in range(n):
        p1 = pts[i].astype(np.float64)
        p2 = pts[(i + 1) % n].astype(np.float64)
        edge = p2 - p1
        length = float(np.linalg.norm(edge))
        # Perpendicular unit normal via left-rotation of the edge direction.
        normal = np.array([-edge[1], edge[0]]) / max(length, 1e-9)
        # Flip to ensure the normal points toward the polygon interior.
        mid = (p1 + p2) / 2.0
        if float(np.dot(normal, centroid - mid)) < 0:
            normal = -normal
        inset_lines.append((p1 + pixels * normal, p2 + pixels * normal))

    # New corner i is the intersection of inset edge (i-1) and inset edge i.
    result = np.empty((n, 2), dtype=np.float64)
    for i in range(n):
        a1, a2 = inset_lines[(i - 1) % n]
        b1, b2 = inset_lines[i]
        da = a2 - a1
        db = b2 - b1
        # Solve: a1 + t*da = b1 + s*db  →  [da | -db] · [t, s]ᵀ = b1 − a1
        mat = np.column_stack([da, -db])
        det = float(np.linalg.det(mat))
        if abs(det) < 1e-9:
            # Parallel edges — use midpoint as fallback.
            result[i] = (a2 + b1) / 2.0
        else:
            t = float(np.linalg.solve(mat, b1 - a1)[0])
            result[i] = a1 + t * da

    return result.astype(np.float32)


def _find_screen_quad(mask: NDArray[np.uint8]) -> NDArray[np.float32]:
    """Return the 4-corner quad of the largest green contour.

    Uses minAreaRect to derive the screen's rotation angle (the globally
    optimal orientation for the whole contour), then recomputes each corner's
    position by projecting the convex-hull points onto the rectangle's own
    axes and taking a trimmed extent (2nd/98th percentile).  The trim discards
    the small bleed protrusions that can push individual minAreaRect corners
    well beyond the actual glass boundary, while leaving the rotation angle
    completely unchanged.

    Returns an array of shape (4, 2) in float32, ordered [TL, TR, BR, BL].
    Raises ValueError if no suitable contour is found.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No green-screen region detected in the avatar image.")

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 500:
        raise ValueError("Green-screen region is too small to be a phone screen.")

    rect = cv2.minAreaRect(largest)
    center, _size, angle = rect

    # Principal axes of the fitted rectangle (unit vectors).
    theta = np.radians(angle)
    axis1 = np.array([np.cos(theta), np.sin(theta)], dtype=np.float64)
    axis2 = np.array([-np.sin(theta), np.cos(theta)], dtype=np.float64)

    # Project the convex hull onto both axes to sample the actual glass extent.
    # Hull points are denser and more representative than the raw contour for
    # this purpose; the trim clips the tail introduced by corner bleed.
    hull_pts = cv2.convexHull(largest).reshape(-1, 2).astype(np.float64)
    center_arr = np.array(center, dtype=np.float64)
    local = hull_pts - center_arr
    proj1 = local @ axis1
    proj2 = local @ axis2

    # 2 % trim on each side: robust enough to remove small corner bleeds while
    # preserving the full glass area for clean screens.
    trim = 2.0
    p1_lo = float(np.percentile(proj1, trim))
    p1_hi = float(np.percentile(proj1, 100.0 - trim))
    p2_lo = float(np.percentile(proj2, trim))
    p2_hi = float(np.percentile(proj2, 100.0 - trim))

    # Recentre on the trimmed extent midpoint so there is no systematic shift.
    new_center = center_arr + ((p1_lo + p1_hi) / 2.0) * axis1 + ((p2_lo + p2_hi) / 2.0) * axis2
    half1 = (p1_hi - p1_lo) / 2.0
    half2 = (p2_hi - p2_lo) / 2.0

    # Build the 4 corners; ordering follows minAreaRect box-point convention so
    # the existing coord-sum/diff ordering logic works unchanged.
    pts = np.array(
        [
            new_center - half1 * axis1 - half2 * axis2,
            new_center + half1 * axis1 - half2 * axis2,
            new_center + half1 * axis1 + half2 * axis2,
            new_center - half1 * axis1 + half2 * axis2,
        ],
        dtype=np.float32,
    )

    coord_sums = pts.sum(axis=1)
    coord_diffs = np.diff(pts, axis=1).flatten()
    return np.array(
        [
            pts[np.argmin(coord_sums)],  # top-left
            pts[np.argmin(coord_diffs)],  # top-right
            pts[np.argmax(coord_sums)],  # bottom-right
            pts[np.argmax(coord_diffs)],  # bottom-left
        ],
        dtype=np.float32,
    )


def _crop_to_content(img_bgr: NDArray[np.uint8], threshold: int = 250) -> NDArray[np.uint8]:
    """Crop image to its non-background content bounding box.

    Pixels where all three channels are >= threshold are considered background
    (white padding).  Returns the original array unchanged if no non-background
    pixels are found.
    """
    non_bg = np.any(img_bgr < threshold, axis=2)
    rows = np.where(non_bg.any(axis=1))[0]
    cols = np.where(non_bg.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return img_bgr
    return img_bgr[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def _rounded_rect_mask(h: int, w: int, radius: int) -> NDArray[np.uint8]:
    """Return a filled white mask of shape (h, w) with rounded corners."""
    mask = np.zeros((h, w), dtype=np.uint8)
    r = min(radius, h // 2, w // 2)
    # Fill the two axis-aligned inner rectangles.
    cv2.rectangle(mask, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(mask, (0, r), (w, h - r), 255, -1)
    # Fill the four rounded corners with filled ellipse quadrants.
    cv2.ellipse(mask, (r, r), (r, r), 180, 0, 90, 255, -1)
    cv2.ellipse(mask, (w - r, r), (r, r), 270, 0, 90, 255, -1)
    cv2.ellipse(mask, (w - r, h - r), (r, r), 0, 0, 90, 255, -1)
    cv2.ellipse(mask, (r, h - r), (r, r), 90, 0, 90, 255, -1)
    return mask


def _warp_screenshot(
    screenshot_bgr: NDArray[np.uint8],
    dst_pts: NDArray[np.float32],
    canvas_shape: tuple[int, int],
    corner_radius_fraction: float = 0.12,
) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    """Perspective-warp the screenshot to fill dst_pts on a blank canvas.

    The source mask has rounded corners (proportional to the shorter screen
    dimension) so that after warping the composited screenshot matches the
    rounded display glass of the phone.

    Returns (warped_image, warp_mask) — both HxW arrays / HxWx3 arrays.
    """
    h, w = screenshot_bgr.shape[:2]
    src_pts = np.array(
        [[0, 0], [w, 0], [w, h], [0, h]],
        dtype=np.float32,
    )
    m = cv2.getPerspectiveTransform(src_pts, dst_pts)
    canvas_h, canvas_w = canvas_shape
    # BORDER_REPLICATE fills outside-quad pixels with the nearest screenshot edge
    # so that green residue at the border is covered with realistic content.
    warped = cv2.warpPerspective(
        screenshot_bgr,
        m,
        (canvas_w, canvas_h),
        borderMode=cv2.BORDER_REPLICATE,
    )
    # Build source mask with rounded corners, then warp it through the same
    # perspective transform so the rounding matches the screen's orientation.
    radius = int(min(h, w) * corner_radius_fraction)
    src_mask = _rounded_rect_mask(h, w, radius)
    # INTER_NEAREST prevents bilinear interpolation from bleeding the binary mask
    # beyond the quad boundary (especially at corners after perspective distortion).
    warp_mask = cv2.warpPerspective(src_mask, m, (canvas_w, canvas_h), flags=cv2.INTER_NEAREST)
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

    # Remove white/neutral padding so the actual phone content fills the screen quad.
    screenshot_bgr = _crop_to_content(screenshot_bgr)

    mask = _build_green_mask(avatar_bgr)
    # Inset the quad corners toward the centroid to counteract the ~7 px per-side
    # expansion introduced by the morphological dilation in _build_green_mask.
    screen_quad = _inset_quad(_find_screen_quad(mask), pixels=10)

    canvas_h, canvas_w = avatar_bgr.shape[:2]
    warped, warp_mask = _warp_screenshot(screenshot_bgr, screen_quad, (canvas_h, canvas_w))

    result = avatar_bgr.copy()
    # Build a raw HSV mask (no morphological ops) for the final clip.  The
    # working `mask` was dilated by ~14 px per side to fill holes and stabilise
    # the contour — this intentionally extends it slightly beyond the actual
    # glass boundary into the bezel, especially at the BR corner where bleed
    # protrusions are common.  Using raw_mask for the final AND guarantees we
    # never paint a dilated-but-not-green (bezel) pixel regardless of which
    # quad method was used.  The raw mask has no interior holes in practice
    # because the green-screen fill is solid; any specular-highlight holes are
    # already covered by warp_mask (which spans the full inset quad).
    hsv = cv2.cvtColor(avatar_bgr, cv2.COLOR_BGR2HSV)
    raw_mask = cv2.inRange(
        hsv,
        np.array([_H_LOW, _S_LOW, _V_LOW], dtype=np.uint8),
        np.array([_H_HIGH, _S_HIGH, _V_HIGH], dtype=np.uint8),
    )
    # eroded_cover: fills the thin ring between the inset-quad boundary and
    # the glass edge that warp_mask alone might not reach.  Use the dilated
    # `mask` here so interior holes from specular highlights are filled.
    _ERODE_COVER_KERNEL = np.ones((5, 5), np.uint8)
    eroded_cover = cv2.erode(mask, _ERODE_COVER_KERNEL, iterations=2)
    composite_mask = cv2.bitwise_or(warp_mask, eroded_cover)
    # Hard clip to raw HSV detections only — strictly inside the glass.
    composite_mask = cv2.bitwise_and(composite_mask, raw_mask)
    result[composite_mask > 0] = warped[composite_mask > 0]

    success, encoded = cv2.imencode(".png", result)
    if not success:
        raise RuntimeError("Failed to encode composite image.")

    return encoded.tobytes()
