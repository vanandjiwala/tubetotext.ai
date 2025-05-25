from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

# app = FastAPI(
#     title="Tubetotext API",
#     description="Youtube video transcription and summarization API",
#     version="1.0.0"
# )

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "api": settings.API_V1_STR
    }