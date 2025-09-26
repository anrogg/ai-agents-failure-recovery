from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uvicorn
import os
from contextlib import asynccontextmanager
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .database import init_db, close_db
from .redis_client import init_redis, close_redis
from .routes import router
from .logging_config import setup_logging
from .metrics import agent_service_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    await init_redis()

    # Set service information for metrics
    agent_service_info.info({
        'version': '1.2.0',
        'environment': 'development',
        'failure_modes_supported': '11'
    })

    yield
    await close_db()
    await close_redis()


app = FastAPI(
    title="AI Agent Failure Recovery Lab",
    description="A system for testing and demonstrating AI agent failure modes and recovery patterns",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)




if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )