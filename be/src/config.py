from pathlib import Path

# Single source of truth for the output directory used by the compositor
# and served as static files.
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Maximum accepted size for each uploaded image (avatar or screenshot).
MAX_IMAGE_BYTES = 16 * 1024 * 1024  # 16 MB
