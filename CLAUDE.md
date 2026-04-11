# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Локальная RAG-система (Retrieval-Augmented Generation) для ответов на вопросы по содержимому `.md`-файлов из директории `admin/knowledge/`. Система разделена на два независимых сервиса, оркестрируемых через общий Docker Compose.

## Project Structure

```
├── docker-compose.yaml          # Оркестрация всех сервисов
├── admin/                       # Сервис администрирования базы знаний
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── knowledge/               # Директория базы знаний (.md файлы)
│   ├── scripts/ollama-entrypoint.sh
│   └── app/                     # config, models, ingestion, main
└── query/                       # Сервис ответов на вопросы
    ├── Dockerfile
    ├── pyproject.toml
    └── app/                     # config, models, retrieval, main
```

Сервисы полностью независимы: у каждого свой Dockerfile, pyproject.toml и код. Общий код не используется.

## Commands

```bash
# Запуск всей системы
docker-compose up --build

# Ручной запуск ingestion (обычно происходит автоматически при старте admin)
curl -X POST http://localhost:8001/ingest

# Запрос к системе
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question": "..."}'
```

Тестов и линтера в проекте пока нет.

## Architecture

Четыре сервиса в Docker Compose:

- **admin** (FastAPI, порт 8001) — `POST /ingest`. Lifespan-хук ожидает готовности Ollama (60 попыток × 10 сек), затем автоматически запускает ingestion.
- **query** (FastAPI, порт 8000) — `POST /ask` (вопрос → ответ на основе RAG-контекста)
- **qdrant** (порт 6333) — векторная БД, volume `qdrant_data`
- **ollama** (порт 11434) — inference-сервер, модели BGE-M3 (embeddings) и Qwen 2.5 7B (LLM), volume `ollama_data`

### Data Flow

1. **Ingestion** (admin): все `.md` файлы из `knowledge/` → чанки (RecursiveCharacterTextSplitter, 300 chars, overlap 100) → embeddings через BGE-M3 → upsert в Qdrant. Коллекция `info_chunks` пересоздаётся при каждом вызове.
2. **Retrieval** (query): вопрос → embedding → поиск top-3 в Qdrant (cosine, threshold 0.3) → контекст + системный промпт → Qwen 2.5 → ответ. Если релевантных чанков нет — «Информация не найдена».

### Key Design Details

- Конфигурация через env-переменные с префиксом `RAG_` (pydantic-settings `BaseSettings`, файл `app/config.py` в каждом сервисе). Ключевые параметры: `ollama_base_url`, `qdrant_host`, `qdrant_port`, `embedding_model`, `llm_model`, `collection_name`, `chunk_size`, `chunk_overlap`, `top_k`, `similarity_threshold`, `knowledge_dir`.
- `admin/knowledge/` монтируется read-only в контейнер по пути `/app/knowledge/`. Для добавления данных — положить `.md` файл в эту директорию и вызвать `POST /ingest`.
- Ollama-контейнер использует кастомный entrypoint (`admin/scripts/ollama-entrypoint.sh`): стартует сервер → подтягивает модели → `wait`. При первом запуске скачивание ~5 ГБ — ждать `All models are ready.` в логах.
- Dockerfiles обоих сервисов идентичны по структуре: `python:3.12-slim`, установка зависимостей через `uv sync --no-dev`, запуск через `uv run uvicorn app.main:app`.

### Dependencies

Общие для обоих сервисов: `fastapi`, `uvicorn`, `qdrant-client`, `ollama`, `pydantic-settings`. Только admin: `langchain-text-splitters`. Python ≥ 3.12.
