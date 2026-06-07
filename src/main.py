import uvicorn
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.auth.routers import router as auth_router
from src.believers.methods_router import router as methods_router
from src.believers.routers import router as believers_router
from src.outreach.routers import router as outreach_statistics_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


app.include_router(auth_router)
app.include_router(methods_router)
app.include_router(believers_router)
app.include_router(outreach_statistics_router)


@app.get("/")
async def health():
    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)