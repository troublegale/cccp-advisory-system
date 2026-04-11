import logging

from fastapi import FastAPI, HTTPException

from app.models import AskRequest, AskResponse
from app.retrieval import ask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Query Service")


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest):
    """Answer a question using the RAG pipeline."""
    try:
        answer = ask(request.question)
        return AskResponse(answer=answer)
    except Exception as e:
        logger.exception("Error processing question")
        raise HTTPException(status_code=500, detail=str(e))
