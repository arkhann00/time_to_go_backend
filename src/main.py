import uvicorn

from fastapi import FastAPI

from src.auth.routers import router as auth_router
from src.believers.methods_router import router as methods_router
from src.believers.routers import router as believers_router


app = FastAPI()


app.include_router(auth_router)
app.include_router(methods_router)
app.include_router(believers_router)


@app.get("/")
async def health():
    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)