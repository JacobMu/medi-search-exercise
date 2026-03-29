# Code Review: Backend API (`be/`)
**Date**: 2026-03-29  
**Reviewer**: GitHub Copilot (SE: Security)  
**Ready for Production**: No  
**Critical Issues**: 4  

---

## Executive Summary

The backend is a FastAPI application for image compositing (green-screen replacement). The codebase is clean and well-structured with good use of type hints, Pydantic validation, and asyncio primitives. However, it has **no authentication layer** and several Denial-of-Service vectors that must be addressed before any internet-facing deployment.

---

## Priority 1 — Must Fix ⛔

### 1. No Authentication on Any Endpoint

**File**: [be/routers/overlay.py](../../be/routers/overlay.py), [be/routers/save.py](../../be/routers/save.py), [be/routers/stats.py](../../be/routers/stats.py)

All four endpoints (`POST /overlay`, `GET /jobs/{job_id}`, `POST /save`, `GET /stats`) are completely unauthenticated. The `/overlay` endpoint spawns CPU-intensive process-pool workers and writes files to disk — an unauthenticated attacker can freely exhaust compute and storage.

**Fix**: Add an API-key dependency (or OAuth2/JWT) as a FastAPI dependency on the router:

```python
# be/dependencies.py
from fastapi import Header, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
import os, secrets

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_EXPECTED_KEY = os.environ["API_KEY"]  # set in environment, never hardcode

async def require_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> None:
    if not api_key or not secrets.compare_digest(api_key, _EXPECTED_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
```

```python
# Apply to every router
router = APIRouter(dependencies=[Depends(require_api_key)])
```

---

### 2. No File Upload Size Limit (DoS via Memory / Disk Exhaustion)

**File**: [be/routers/overlay.py](../../be/routers/overlay.py#L56)

```python
# CURRENT — unbounded read
avatar_bytes = await avatar.read()
screenshot_bytes = await screenshot.read()
```

There is no cap on how many bytes are read. A multi-gigabyte upload will be fully buffered into memory before any validation occurs.

**Fix**: Enforce a size limit before reading:

```python
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

async def _read_limited(upload: UploadFile, name: str) -> bytes:
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{name} exceeds 10 MB limit.")
    return data

avatar_bytes = await _read_limited(avatar, "avatar")
screenshot_bytes = await _read_limited(screenshot, "screenshot")
```

---

### 3. PIL Decompression Bomb (DoS via Memory Exhaustion)

**File**: [be/services/compositor.py](../../be/services/compositor.py#L42)

```python
# CURRENT — no pixel limit
img = Image.open(io.BytesIO(data))
```

PIL raises `DecompressionBombError` only above 178 MP by default, but this limit can be trivially circumvented with crafted images or simply by using the allowed headroom. A 178 MP RGBA image occupies ~700 MB of RAM.

**Fix**: Set a strict pixel budget at application startup and explicitly handle the error:

```python
from PIL import Image
Image.MAX_IMAGE_PIXELS = 4000 * 4000  # ~16 MP — sufficient for phone screenshots

def _bytes_to_rgb_array(data: bytes) -> NDArray[np.uint8]:
    try:
        img = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError as exc:
        raise ValueError("Image dimensions exceed the allowed limit.") from exc
    ...
```

---

### 4. Raw Exception Messages Returned to Clients (Information Disclosure)

**File**: [be/routers/overlay.py](../../be/routers/overlay.py#L45), [be/store/jobs.py](../../be/store/jobs.py#L44)

```python
# CURRENT — raw exception string stored and exposed via GET /jobs/{job_id}
except Exception as exc:
    await job_store.set_failed(job_id, str(exc))
```

Internal error messages (file paths, library versions, stack hints) are stored verbatim and later returned in the public API response at `payload["error"] = record.error`.

**Fix**: Log the full exception server-side and store only a sanitised user-facing message:

```python
import logging
logger = logging.getLogger(__name__)

except Exception as exc:
    logger.exception("Compositing failed for job %s", job_id)
    user_msg = str(exc) if isinstance(exc, ValueError) else "Internal processing error."
    await job_store.set_failed(job_id, user_msg)
```

Only `ValueError` (raised intentionally with user-facing messages in `compositor.py`) is surfaced; all other exceptions produce a generic message.

---

## Priority 2 — Should Fix ⚠️

### 5. No Rate Limiting on Compute-Intensive Endpoints

**File**: [be/routers/overlay.py](../../be/routers/overlay.py)

A single client can submit hundreds of jobs per second. Combined with the lack of auth, this is a trivial DoS vector.

**Fix**: Add `slowapi` (or an upstream proxy like nginx) rate limiting:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/overlay", status_code=202)
@limiter.limit("10/minute")
async def overlay(request: Request, avatar: UploadFile, screenshot: UploadFile):
    ...
```

---

### 6. Unbounded In-Memory Job Store (DoS via Memory Exhaustion)

**File**: [be/store/jobs.py](../../be/store/jobs.py)

`JobStore._store` is an unbounded `dict`. Jobs are never evicted. Under sustained use the process will exhaust available memory.

**Fix**: Add a maximum capacity with LRU eviction or a TTL-based cleanup task:

```python
MAX_JOBS = 10_000

async def create(self, job_id: str) -> JobRecord:
    async with self._lock:
        if len(self._store) >= MAX_JOBS:
            raise HTTPException(status_code=503, detail="Job queue is full.")
        ...
```

---

### 7. No Content-Type Validation for Uploaded Files

**File**: [be/routers/overlay.py](../../be/routers/overlay.py#L55)

The `content_type` attribute of `UploadFile` is available but never checked, allowing upload of arbitrary binary content (scripts, archives, etc.) that will be passed directly into image parsing libraries.

**Fix**: Validate the MIME type allowlist before processing:

```python
_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}

def _assert_image_type(upload: UploadFile, name: str) -> None:
    if upload.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"{name} must be PNG, JPEG, or WebP (got {upload.content_type!r}).",
        )

_assert_image_type(avatar, "avatar")
_assert_image_type(screenshot, "screenshot")
```

Note: `content_type` is client-supplied and not a hard guarantee; pair this with magic-byte verification for higher assurance.

---

### 8. No UUID Format Validation on `job_id` Path / Body Parameter

**File**: [be/routers/overlay.py](../../be/routers/overlay.py#L80), [be/models/analytics.py](../../be/models/analytics.py)

`job_id` is declared as plain `str` both in the URL path and in `SaveRequest`. Any string (including very long or specially crafted ones) is accepted.

**Fix**: Use a `uuid.UUID` type so FastAPI/Pydantic validates the format automatically:

```python
# models/analytics.py
from uuid import UUID
class SaveRequest(BaseModel):
    job_id: UUID
    ...

# routers/overlay.py
from uuid import UUID
@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID) -> JSONResponse:
    record = await job_store.get(str(job_id))
    ...
```

---

## Priority 3 — Consider ℹ️

### 9. Output Directory Publicly Accessible Without Auth

**File**: [be/main.py](../../be/main.py#L14)

```python
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
```

All generated composite images are served from a public static route. Any caller who knows (or guesses) a UUID can download any composited image. If images contain sensitive content, they should be served through an authenticated endpoint rather than a public `StaticFiles` mount.

---

### 10. `0.0.0.0` Binding in Development Entry Point

**File**: [be/main.py](../../be/main.py#L22)

```python
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104
```

Binding to `0.0.0.0` with `reload=True` is acceptable in containers but exposes the server on all network interfaces when run locally. The `# noqa: S104` suppresses the Bandit warning without addressing the underlying risk. Add a note or an environment-variable override:

```python
import os
HOST = os.getenv("HOST", "127.0.0.1")  # default to loopback for local dev
uvicorn.run("main:app", host=HOST, port=8000, reload=True)
```

---

### 11. No CORS Policy

**File**: [be/main.py](../../be/main.py)

No `CORSMiddleware` is configured. If a browser-based frontend will call this API, an explicit CORS allowlist should be defined rather than relying on the default (deny-all):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.example.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

---

### 12. No Upper Bound on `processing_time_ms` in `SaveRequest`

**File**: [be/models/analytics.py](../../be/models/analytics.py#L7)

```python
processing_time_ms: int = Field(..., ge=0)
```

An adversary could submit an astronomically large value to inflate the `avg_processing_time_ms` aggregate stat. Add a reasonable upper bound:

```python
processing_time_ms: int = Field(..., ge=0, le=300_000)  # 5 minutes max
```

---

## Summary Table

| # | Severity | Category | File | Issue |
|---|----------|----------|------|-------|
| 1 | Critical | A01 Broken Access Control | routers/* | No authentication |
| 2 | Critical | A05 Security Misconfiguration | routers/overlay.py | No upload size limit |
| 3 | Critical | A05 Security Misconfiguration | services/compositor.py | PIL decompression bomb |
| 4 | Critical | A09 Security Logging/Monitoring | routers/overlay.py | Raw exceptions exposed |
| 5 | High | A04 Insecure Design | routers/overlay.py | No rate limiting |
| 6 | High | A04 Insecure Design | store/jobs.py | Unbounded job store |
| 7 | High | A03 Injection | routers/overlay.py | No content-type validation |
| 8 | Medium | A03 Injection | routers/overlay.py, models/analytics.py | No job_id format validation |
| 9 | Medium | A01 Broken Access Control | main.py | Output files publicly accessible |
| 10 | Low | A05 Security Misconfiguration | main.py | 0.0.0.0 binding |
| 11 | Low | A05 Security Misconfiguration | main.py | No CORS policy |
| 12 | Low | A04 Insecure Design | models/analytics.py | Unbounded processing_time_ms |
