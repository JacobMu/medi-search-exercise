from fastapi import HTTPException, UploadFile, status


async def read_limited(upload: UploadFile, limit: int, field: str) -> bytes:
    """Read *upload* in chunks up to *limit* bytes.

    Raises HTTP 413 as soon as the stream exceeds *limit* so we never buffer
    the full oversized payload in memory.
    """
    chunks: list[bytes] = []
    total = 0
    chunk_size = 64 * 1024  # 64 KB
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"'{field}' exceeds the {limit // (1024 * 1024)} MB size limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)
