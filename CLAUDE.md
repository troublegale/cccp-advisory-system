# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Локальная RAG-система (Retrieval-Augmented Generation) для ответов на вопросы по содержимому файла `info.md`. Система разделена на два независимых сервиса, оркестрируемых через общий Docker Compose.

## Project Structure

```
├── docker-compose.yaml          # Оркестрация всех сервисов
├── admin/                       # Сервис администрирования базы знаний
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── info.md                  # Файл базы знаний
│   ├── scripts/ollama-entrypoint.sh
│   └── app/                     # config, models, ingestion, main
└── query/                       # Сервис ответов на вопросы
    ├── Dockerfile
    ├─��� pyproject.toml
    └── app/                     # config, models, retrieval, main
```

Сервисы полностью независимы: у каждого свой Dockerfile, pyproject.toml и код. Общий код не используется.

## Commands

```bash
# Запуск всей системы
docker-compose up --build

# Проверка API
curl -X POST http://localhost:8001/ingest
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question": "..."}'
```

Тестов и линтера в проекте пока нет.

## Architecture

Четыре сервиса в Docker Compose:

- **admin** (FastAPI, порт 8001) — администрирование базы знаний: `POST /ingest`. При старте ожидает готовности Ollama-моделей и автоматически запускает ingestion.
- **query** (FastAPI, порт 8000) — пользовательские запросы: `POST /ask` (вопрос → ответ)
- **qdrant** (порт 6333) — векторная БД для хранения эмбеддингов чанков
- **ollama** (порт 11434) — локальный inference-сервер для моделей BGE-M3 (embeddings) и Qwen 2.5 7B (LLM)

### Data Flow

1. **Ingestion** (admin): чтение `info.md` → разбивка на чанки (RecursiveCharacterTextSplitter, 300 символов, overlap 100) → эмбеддинги через Ollama BGE-M3 → upsert в Qdrant. Коллекция пересоздаётся при каждом вызове.
2. **Retrieval** (query): вопрос → эмбеддинг → поиск top-K в Qdrant (cosine, threshold 0.3) → контекст + системный промпт → Qwen 2.5 → ответ. Если релевантных чанков нет, возвращает «Информация не найдена».

### Key Design Details

- Конфигурация через env-переменные с префиксом `RAG_` (pydantic-settings, `app/config.py` в каждом сервисе)
- При старте admin-сервиса lifespan-хук ожидает готовности Ollama-моделей (до 10 минут, 60 попыток × 10 сек) и автоматически запускает ingestion
- `admin/info.md` монтируется read-only в контейнер admin по пути `/app/info.md`
- Ollama-контейнер использует кастомный entrypoint (`admin/scripts/ollama-entrypoint.sh`), который стартует сервер и подтягивает модели
- При первом запуске Ollama скачивает модели (~5 ГБ) — нужно дождаться сообщения `All models are ready.` в логах
