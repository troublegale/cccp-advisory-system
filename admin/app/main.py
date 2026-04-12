import logging
import time
from contextlib import asynccontextmanager

import ollama
from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.storage import ensure_bucket_exists, get_minio_client
from app.router import router as kb_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 60
RETRY_DELAY = 10


def wait_for_ollama_models() -> None:
    """Wait until Ollama has the required models pulled and ready."""
    client = ollama.Client(host=settings.ollama_base_url)
    required = {settings.embedding_model.split(":")[0], settings.llm_model.split(":")[0]}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.list()
            available = {m.model.split(":")[0] for m in response.models}
            missing = required - available
            if not missing:
                logger.info("All Ollama models are available")
                return
            logger.info(
                "Waiting for models %s (attempt %d/%d)...",
                missing, attempt, MAX_RETRIES,
            )
        except Exception:
            logger.info(
                "Ollama not reachable yet (attempt %d/%d)...",
                attempt, MAX_RETRIES,
            )
        time.sleep(RETRY_DELAY)

    raise RuntimeError("Ollama models did not become available in time")


def init_infrastructure() -> None:
    """Create database tables and MinIO bucket."""
    # Import models so Base.metadata knows about them
    import app.db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    s3 = get_minio_client()
    ensure_bucket_exists(s3, settings.minio_kb_bucket)
    logger.info("MinIO bucket '%s' ensured", settings.minio_kb_bucket)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize infrastructure and wait for Ollama models on startup."""
    init_infrastructure()
    wait_for_ollama_models()
    yield


app = FastAPI(title="RAG Admin Service", lifespan=lifespan)
app.include_router(kb_router)
