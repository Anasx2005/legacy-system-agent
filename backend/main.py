"""FastAPI main application entrypoint."""

from fastapi import FastAPI

from backend.api.ingestion import router as ingestion_router
from backend.api.webhooks import router as webhooks_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Legacy System Architecture Recovery API",
    description="Control Plane & Webhook Receiver for ArchiMate model ingestion pipeline",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


app.include_router(webhooks_router)
app.include_router(ingestion_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "legacy-system-agent"}
