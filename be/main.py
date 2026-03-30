import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import OUTPUT_DIR
from src.overlay.router import router as overlay_router
from src.save.router import router as save_router
from src.stats.router import router as stats_router

app = FastAPI(
    title="Ad Creatives Compositor",
    description="Programmatically replace green-screen phone displays with app screenshots.",
    version="0.1.0",
)

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

app.include_router(overlay_router)
app.include_router(save_router)
app.include_router(stats_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104
