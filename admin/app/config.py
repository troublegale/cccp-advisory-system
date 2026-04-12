from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    embedding_model: str = "bge-m3"
    llm_model: str = "qwen2.5:7b"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333

    # Chunking
    chunk_size: int = 300
    chunk_overlap: int = 100

    # Legacy (used only by seed script)
    collection_name: str = "info_chunks"
    knowledge_dir: str = "/app/knowledge"

    # PostgreSQL
    database_url: str = "postgresql+psycopg2://admin:secret@postgres:5432/admin_db"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_kb_bucket: str = "knowledge-base"
    minio_use_ssl: bool = False

    # KB versioning
    kb_collection_prefix: str = "kb_v"
    kb_active_alias: str = "kb_active"

    model_config = {"env_prefix": "RAG_"}


settings = Settings()
