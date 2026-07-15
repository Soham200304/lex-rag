from fastapi import FastAPI
from app.routers.health import router as health_router
app = FastAPI(
    title="LexRAG API",
    description="AI-powered Legal Retrieval-Augmented Generation Backend",
    version="0.1.0",
)

app.include_router(health_router)