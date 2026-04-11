import logging
from pathlib import Path

import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)


def read_and_split(file_path: str) -> list[str]:
    """Read info.md and split into chunks."""
    text = Path(file_path).read_text(encoding="utf-8")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_text(text)
    logger.info("Split %s into %d chunks", file_path, len(chunks))
    return chunks


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts via Ollama."""
    client = ollama.Client(host=settings.ollama_base_url)
    response = client.embed(model=settings.embedding_model, input=texts)
    return response.embeddings


def ingest() -> int:
    """Full ingestion pipeline: read, chunk, embed, store in Qdrant."""
    chunks = read_and_split(settings.info_file_path)
    embeddings = get_embeddings(chunks)
    vector_size = len(embeddings[0])

    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    # Recreate collection to ensure clean state
    if qdrant.collection_exists(settings.collection_name):
        qdrant.delete_collection(settings.collection_name)

    qdrant.create_collection(
        collection_name=settings.collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

    points = [
        PointStruct(id=i, vector=emb, payload={"text": chunk})
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]
    qdrant.upsert(collection_name=settings.collection_name, points=points)

    logger.info("Ingested %d chunks into Qdrant", len(chunks))
    return len(chunks)
