from pathlib import Path

# Single source of truth for the output directory used by the compositor
# and served as static files.
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
