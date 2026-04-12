from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://ollama:11434"
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    embedding_model: str = "bge-m3"
    llm_model: str = "qwen2.5:7b"
    collection_name: str = "kb_active"
    top_k: int = 3
    similarity_threshold: float = 0.3

    model_config = {"env_prefix": "RAG_"}


settings = Settings()
