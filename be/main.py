import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import OUTPUT_DIR
from routers import overlay, save, stats

app = FastAPI(
    title="Ad Creatives Compositor",
    description="Programmatically replace green-screen phone displays with app screenshots.",
    version="0.1.0",
)

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

app.include_router(overlay.router)
app.include_router(save.router)
app.include_router(stats.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104
