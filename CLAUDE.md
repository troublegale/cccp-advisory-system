# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Локальная RAG-система (Retrieval-Augmented Generation) с версионированием базы знаний. `.md`-файлы загружаются через API в виде `.zip`-архивов, хранятся в MinIO, метаданные версий — в PostgreSQL, векторные индексы — в Qdrant. Два независимых FastAPI-сервиса (admin и query) с общей инфраструктурой оркестрируются через Docker Compose.

Сервисы полностью независимы: у каждого свой Dockerfile, `pyproject.toml` и код. Общий код не используется — при изменении конфигурации или моделей нужно обновлять оба `app/config.py`.

## Commands

```bash
# Запуск всей системы (первый запуск: ~5 ГБ скачивание моделей)
docker compose up --build -d

# Загрузка новой версии базы знаний (сразу индексируется в Qdrant)
curl -X POST http://localhost/api/v1/knowledge-base/versions -F "archive=@knowledge.zip"

# Активация версии
curl -X POST http://localhost/api/v1/knowledge-base/versions/1/activate

# Информация об активной версии / скачивание её архива
curl http://localhost/api/v1/knowledge-base/versions/active
curl -O http://localhost/api/v1/knowledge-base/versions/active/archive

# Запрос к системе
curl -X POST http://localhost/ask -H "Content-Type: application/json" -d '{"question": "..."}'

# Seed-скрипт: импорт legacy-файлов из knowledge/ как версию 1
docker compose exec admin uv run python scripts/seed_kb_v1.py
```

Тестов и линтера в проекте нет. Менеджер пакетов — `uv` (установка: `uv sync --no-dev`, запуск: `uv run uvicorn app.main:app`).

## Architecture

Семь сервисов в Docker Compose:

- **nginx** (порт 80) — единая точка входа, проксирует `/api/v1/knowledge-base/` -> admin, `/ask` -> query.
- **admin** (внутренний, порт 8001) — управление версиями базы знаний: загрузка с автоматической индексацией, активация, скачивание, удаление. Lifespan-хук создаёт таблицы в PostgreSQL и bucket в MinIO, затем ожидает готовности моделей в Ollama.
- **query** (внутренний, порт 8000) — `POST /ask` (вопрос -> RAG-ответ). Включает `EncodingMiddleware` для прозрачной перекодировки non-UTF-8 тел запросов (fallback: windows-1251, cp866, koi8-r, iso-8859-5).
- **postgres** (порт 5432) — метаданные версий (`kb_versions`, `kb_files`), volume `postgres_data`.
- **minio** (порты 9000/9001) — S3-совместимое хранилище файлов базы знаний, volume `minio_data`. Консоль: `http://localhost:9001`.
- **qdrant** (порт 6333) — векторная БД, volume `qdrant_data`.
- **ollama** (порт 11434) — inference-сервер, volume `ollama_data`.

Прямой доступ к admin и query закрыт — только через nginx.

### Version Lifecycle

```
Upload (.zip) -> ingested (автоматическая индексация) -> POST /activate -> active
```

При загрузке архива файлы сохраняются в MinIO, затем сразу индексируются в Qdrant (коллекция `kb_v{N}`). Версия переходит в статус `ingested`. После активации alias `kb_active` указывает на коллекцию, query-сервис использует только этот alias. Старые коллекции не удаляются (возможен откат). Активную версию нельзя удалить — сначала нужно активировать другую.

### Data Flow

1. **Upload + Ingest** (`admin/app/service.py`): `.zip`-архив -> извлечение `.md` файлов -> MinIO (`versions/v{N}/`) -> метаданные в PostgreSQL -> чанки (RecursiveCharacterTextSplitter, 300 chars, overlap 100) -> embeddings через BGE-M3 -> коллекция `kb_v{N}` в Qdrant.
2. **Activation** (`admin/app/service.py`): alias `kb_active` -> `kb_v{N}`, предыдущая активная версия переводится в `ingested`.
3. **Retrieval** (`query/app/retrieval.py`): вопрос -> embedding -> поиск top-3 в `kb_active` (cosine, threshold 0.3) -> контекст + русскоязычный системный промпт (hardcoded в `SYSTEM_PROMPT`) -> Qwen 2.5 7B -> ответ.

### Key Design Details

- **Конфигурация** через env-переменные с префиксом `RAG_` (pydantic-settings `BaseSettings`, файл `app/config.py` в каждом сервисе). Admin-конфиг включает настройки PostgreSQL (`database_url`), MinIO (`minio_endpoint`, `minio_access_key`, `minio_secret_key`, `minio_kb_bucket`), чанкинга и версионирования (`kb_collection_prefix`, `kb_active_alias`).
- **Дублирование моделей**: имена моделей (`bge-m3`, `qwen2.5:7b`) заданы в трёх местах — `admin/app/config.py`, `query/app/config.py` и `admin/scripts/ollama-entrypoint.sh`. При смене модели нужно обновить все три.
- **БД-таблицы** создаются автоматически при старте admin через `Base.metadata.create_all`. Alembic настроен для будущих миграций (`admin/alembic/`).
- **Legacy**: `admin/knowledge/` монтируется read-only для seed-скрипта. Директория больше не является источником данных — файлы хранятся в MinIO.
- Ollama-контейнер использует кастомный entrypoint (`admin/scripts/ollama-entrypoint.sh`): стартует `ollama serve` в фоне -> подтягивает модели -> `wait`.
- Dockerfiles обоих сервисов: `python:3.12-slim`, `uv` из `ghcr.io/astral-sh/uv:latest`, установка через `uv sync --no-dev`. Admin дополнительно копирует `alembic/` и `scripts/`.
