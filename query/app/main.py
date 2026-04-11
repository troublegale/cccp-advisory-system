import logging
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.models import AskRequest, AskResponse
from app.retrieval import ask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FALLBACK_ENCODINGS = ["windows-1251", "cp866", "koi8-r", "iso-8859-5"]
GARBLED_PATTERN = re.compile(r"\?{3,}")


class EncodingMiddleware(BaseHTTPMiddleware):
    """Re-encode non-UTF-8 request bodies to UTF-8 transparently."""

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            try:
                body.decode("utf-8")
            except UnicodeDecodeError:
                for enc in FALLBACK_ENCODINGS:
                    try:
                        decoded = body.decode(enc)
                        request._body = decoded.encode("utf-8")
                        logger.info("Re-encoded request body from %s to UTF-8", enc)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Request body encoding not recognized. Use UTF-8."},
                    )
        return await call_next(request)


app = FastAPI(title="RAG Query Service")
app.add_middleware(EncodingMiddleware)


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest):
    """Answer a question using the RAG pipeline."""
    if request.question.isascii() and GARBLED_PATTERN.search(request.question):
        raise HTTPException(
            status_code=400,
            detail="Question appears to have encoding issues (contains only ASCII "
            "with repeated '?' characters). Send the request in UTF-8 encoding.",
        )
    try:
        answer = ask(request.question)
        return AskResponse(answer=answer)
    except Exception as e:
        logger.exception("Error processing question")
        raise HTTPException(status_code=500, detail=str(e))
