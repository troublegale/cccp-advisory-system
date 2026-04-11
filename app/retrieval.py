import logging

import ollama
from qdrant_client import QdrantClient

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — полезный ИИ-ассистент. Отвечай на вопросы пользователя, "
    "используя ТОЛЬКО предоставленный контекст. "
    "Если в контексте недостаточно информации для ответа, "
    'ответь строго: "Информация не найдена".'
)


def ask(question: str) -> str:
    """Embed the question, search Qdrant, generate an answer via LLM."""
    client = ollama.Client(host=settings.ollama_base_url)

    # Embed the query
    response = client.embed(model=settings.embedding_model, input=[question])
    query_vector = response.embeddings[0]

    # Search Qdrant
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    response = qdrant.query_points(
        collection_name=settings.collection_name,
        query=query_vector,
        limit=settings.top_k,
        score_threshold=settings.similarity_threshold,
    )
    results = response.points

    if not results:
        return "Информация не найдена"

    # Build context from search results
    context = "\n\n".join(hit.payload["text"] for hit in results)
    logger.info(
        "Found %d relevant chunks (scores: %s)",
        len(results),
        [round(hit.score, 3) for hit in results],
    )

    # Generate answer via LLM
    user_message = (
        f"Контекст:\n{context}\n\n"
        f"Вопрос: {question}\n\n"
        "Ответь на вопрос, используя только информацию из контекста выше."
    )

    llm_response = client.chat(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    return llm_response.message.content
