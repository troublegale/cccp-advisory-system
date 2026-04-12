# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Локальная RAG-система (Retrieval-Augmented Generation) для ответов на вопросы по содержимому `.md`-файлов из директории `admin/knowledge/`. Два независимых FastAPI-сервиса (admin и query) с общей инфраструктурой (Qdrant, Ollama) оркестрируются через Docker Compose.

Сервисы полностью независимы: у каждого свой Dockerfile, `pyproject.toml` и код. Общий код не используется — при изменении конфигурации или моделей нужно обновлять оба `app/config.py`.

## Commands

```bash
# Запуск всей системы (первый запуск: ~5 ГБ скачивание моделей)
docker-compose up --build

# Ручной запуск ingestion (автоматически происходит при старте admin)
curl -X POST http://localhost:8001/ingest

# Запрос к системе
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question": "..."}'
```

Тестов и линтера в проекте нет. Менеджер пакетов — `uv` (установка: `uv sync --no-dev`, запуск: `uv run uvicorn app.main:app`).

## Architecture

Четыре сервиса в Docker Compose:

- **admin** (порт 8001) — `POST /ingest`. Lifespan-хук ожидает готовности моделей в Ollama (60 попыток x 10 сек), затем автоматически запускает ingestion.
- **query** (порт 8000) — `POST /ask` (вопрос -> RAG-ответ). Включает `EncodingMiddleware` для прозрачной перекодировки non-UTF-8 тел запросов (fallback: windows-1251, cp866, koi8-r, iso-8859-5).
- **qdrant** (порт 6333) — векторная БД, volume `qdrant_data`.
- **ollama** (порт 11434) — inference-сервер, volume `ollama_data`.

### Data Flow

1. **Ingestion** (`admin/app/ingestion.py`): все `.md` файлы из `knowledge/` -> чанки (RecursiveCharacterTextSplitter, 300 chars, overlap 100) -> embeddings через BGE-M3 -> upsert в Qdrant. **Коллекция `info_chunks` полностью пересоздаётся при каждом вызове** — это destructive operation, все предыдущие данные удаляются.
2. **Retrieval** (`query/app/retrieval.py`): вопрос -> embedding -> поиск top-3 в Qdrant (cosine, threshold 0.3) -> контекст + русскоязычный системный промпт (hardcoded в `SYSTEM_PROMPT`) -> Qwen 2.5 7B -> ответ. Если релевантных чанков нет — «Информация не найдена».

### Key Design Details

- **Конфигурация** через env-переменные с префиксом `RAG_` (pydantic-settings `BaseSettings`, файл `app/config.py` в каждом сервисе). Конфиги admin и query дублируют общие поля (`ollama_base_url`, `qdrant_host`, `qdrant_port`, `embedding_model`, `llm_model`, `collection_name`), admin добавляет `chunk_size`, `chunk_overlap`, `knowledge_dir`, query — `top_k`, `similarity_threshold`.
- **Дублирование моделей**: имена моделей (`bge-m3`, `qwen2.5:7b`) заданы в трёх местах — `admin/app/config.py`, `query/app/config.py` и `admin/scripts/ollama-entrypoint.sh`. При смене модели нужно обновить все три.
- `admin/knowledge/` монтируется read-only в контейнер по пути `/app/knowledge/`. Для добавления данных — положить `.md` файл и вызвать `POST /ingest`.
- Ollama-контейнер использует кастомный entrypoint (`admin/scripts/ollama-entrypoint.sh`): стартует `ollama serve` в фоне -> подтягивает модели -> `wait`.
- Dockerfiles обоих сервисов идентичны по структуре: `python:3.12-slim`, копирование `uv` из `ghcr.io/astral-sh/uv:latest`, установка через `uv sync --no-dev`.
