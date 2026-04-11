import logging
from pathlib import Path

import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)


def read_and_split(knowledge_dir: str) -> list[str]:
    """Read all .md files from the knowledge directory and split into chunks."""
    directory = Path(knowledge_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Knowledge directory not found: {knowledge_dir}")

    md_files = sorted(directory.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md files found in {knowledge_dir}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    all_chunks = []
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(text)
        logger.info("Split %s into %d chunks", md_file.name, len(chunks))
        all_chunks.extend(chunks)

    return all_chunks


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts via Ollama."""
    client = ollama.Client(host=settings.ollama_base_url)
    response = client.embed(model=settings.embedding_model, input=texts)
    return response.embeddings


def ingest() -> int:
    """Full ingestion pipeline: read, chunk, embed, store in Qdrant."""
    chunks = read_and_split(settings.knowledge_dir)
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
