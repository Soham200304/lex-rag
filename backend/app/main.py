from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.check_db import check_database
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_database()
    print("Database connected successfully.")

    yield


app = FastAPI(
    title="LexRAG API",
    description="AI-powered Legal Retrieval-Augmented Generation Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)