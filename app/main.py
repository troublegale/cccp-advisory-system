import logging
import time
from contextlib import asynccontextmanager

import ollama
from fastapi import FastAPI, HTTPException

from app.config import settings
from app.ingestion import ingest
from app.models import AskRequest, AskResponse, IngestResponse
from app.retrieval import ask

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wait for Ollama models, then run ingestion on startup."""
    wait_for_ollama_models()
    logger.info("Starting ingestion pipeline...")
    try:
        count = ingest()
        logger.info("Ingestion complete: %d chunks indexed", count)
    except Exception:
        logger.exception("Ingestion failed on startup")
    yield


app = FastAPI(title="RAG Prototype", lifespan=lifespan)


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest):
    """Answer a question using the RAG pipeline."""
    try:
        answer = ask(request.question)
        return AskResponse(answer=answer)
    except Exception as e:
        logger.exception("Error processing question")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", response_model=IngestResponse)
def ingest_endpoint():
    """Re-read info.md and update the vector database."""
    try:
        count = ingest()
        return IngestResponse(status="ok", chunks_count=count)
    except Exception as e:
        logger.exception("Error during ingestion")
        raise HTTPException(status_code=500, detail=str(e))
