# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Локальная RAG-система (Retrieval-Augmented Generation) с версионированием базы знаний. `.md`-файлы загружаются через API в виде `.zip`-архивов, хранятся в MinIO, метаданные версий — в PostgreSQL, векторные индексы — в Qdrant. Два независимых FastAPI-сервиса (admin и query) + два React-фронтенда (admin-frontend и query-widget) с общей инфраструктурой оркестрируются через Docker Compose.

Backend-сервисы полностью независимы: у каждого свой Dockerfile, `pyproject.toml` и код. Общий код не используется — при изменении конфигурации или моделей нужно обновлять оба `app/config.py`. Фронтенды также независимы: у каждого свой `package.json`, Vite-сборка и nginx в продакшен-образе.

## Commands

```bash
# Запуск всей системы (первый запуск: ~5 ГБ скачивание моделей)
docker compose up --build -d

# Просмотр логов (полезно для отладки, особенно ожидания моделей)
docker compose logs -f admin
docker compose logs -f query
docker compose logs -f ollama   # дождаться "All models are ready."

# Пересборка отдельного сервиса после изменений в коде
docker compose up --build -d admin
docker compose up --build -d query
docker compose up --build -d admin-frontend
docker compose up --build -d query-widget

# Локальная разработка фронтендов без Docker (Vite dev server)
cd admin-frontend && npm install && npm run dev      # http://localhost:5173
cd query-widget  && npm install && npm run dev       # требуется запущенный backend на :80 для /ask

# Продакшен-сборка фронтенда (tsc + vite build, выходит в dist/)
cd admin-frontend && npm run build

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

Тестов и линтера в проекте нет. Менеджер пакетов для backend — `uv` (установка: `uv sync --no-dev`, запуск: `uv run uvicorn app.main:app`). Для фронтендов — `npm` (Node 20/22 alpine в Dockerfile).

## Architecture

Девять сервисов в Docker Compose:

- **nginx** (порт 80) — единая точка входа. Маршрутизация: `/api/v1/knowledge-base/` → admin (лимит тела 50 МБ), `/ask` → query, `/widget` → query-widget (с rewrite), `/demo` → статический `demo.html` (пример встраивания виджета через iframe), `/` → admin-frontend (SPA). Конфиг — `nginx/nginx.conf`.
- **admin** (внутренний, порт 8001) — FastAPI, управление версиями базы знаний: загрузка с автоматической индексацией, активация, скачивание, удаление. Lifespan-хук создаёт таблицы в PostgreSQL и bucket в MinIO, затем ожидает готовности моделей в Ollama (до 10 минут, polling каждые 10 секунд).
- **query** (внутренний, порт 8000) — FastAPI, `POST /ask` (вопрос → RAG-ответ). Включает `EncodingMiddleware` для прозрачной перекодировки non-UTF-8 тел запросов (fallback: windows-1251, cp866, koi8-r, iso-8859-5).
- **admin-frontend** (внутренний, порт 3000) — React 19 + Vite SPA для управления версиями базы знаний (загрузка `.zip`, активация, просмотр, удаление). Использует относительные пути `/api/v1/knowledge-base/*` — все запросы идут через nginx к admin. Сборка — multi-stage Dockerfile: `npm run build` → nginx:alpine, раздающий `dist/`.
- **query-widget** (внутренний, порт 3001) — React 18 + Vite чат-виджет с floating action button. Встраивается на внешние страницы как iframe (`<iframe src="http://localhost/widget/">`). `API_BASE = window.location.origin` — в режиме iframe запросы идут на хост родительской страницы, поэтому виджет должен раздаваться с того же origin, где доступен `/ask`.
- **postgres** (внутренний) — метаданные версий (`kb_versions`, `kb_files`), volume `postgres_data`.
- **minio** (внутренний) — S3-совместимое хранилище файлов базы знаний через `boto3` (не minio SDK), volume `minio_data`.
- **qdrant** (внутренний) — векторная БД, volume `qdrant_data`.
- **ollama** (внутренний) — inference-сервер, volume `ollama_data`.

Прямой доступ ко всем сервисам кроме nginx закрыт — единственный внешний порт 80 у nginx.

### Version Lifecycle

```
Upload (.zip) → uploaded → (auto-ingest) → ingested → POST /activate → active
                                          ↘ failed (при ошибке индексации)
```

Статусы: `uploaded` (файлы в MinIO, ещё не индексированы — транзитный), `ingested` (индексация завершена, готова к активации), `active` (alias `kb_active` указывает на коллекцию), `failed` (ошибка при индексации). На практике `uploaded` → `ingested` происходит в рамках одного запроса `upload_version`.

Активную версию нельзя удалить — сначала нужно активировать другую. Старые коллекции не удаляются (возможен откат).

### Data Flow

1. **Upload + Ingest** (`admin/app/service.py`): `.zip`-архив → извлечение `.md` файлов (скрытые файлы и директории игнорируются) → MinIO (`versions/v{N}/`) → метаданные в PostgreSQL → чанки (RecursiveCharacterTextSplitter, 300 chars, overlap 100) → embeddings через BGE-M3 (один батч на всю версию) → коллекция `kb_v{N}` в Qdrant.
2. **Activation** (`admin/app/service.py`): атомарное переключение alias `kb_active` → `kb_v{N}` (delete old alias + create new в одной операции), предыдущая активная версия переводится в `ingested`.
3. **Retrieval** (`query/app/retrieval.py`): вопрос → embedding → поиск top-3 в `kb_active` (cosine, threshold 0.3) → контекст + русскоязычный системный промпт (hardcoded в `SYSTEM_PROMPT`) → Qwen 2.5 7B → ответ. Если ни один чанк не прошёл порог — сразу возвращает `"Информация не найдена"` без обращения к LLM.

### Key Design Details

- **Конфигурация** через env-переменные с префиксом `RAG_` (pydantic-settings `BaseSettings`, файл `app/config.py` в каждом сервисе). Синглтон `settings = Settings()` на уровне модуля.
- **Дублирование моделей**: имена моделей (`bge-m3`, `qwen2.5:7b`) заданы в трёх местах — `admin/app/config.py`, `query/app/config.py` и `admin/scripts/ollama-entrypoint.sh`. При смене модели нужно обновить все три.
- **MinIO-клиент** — используется `boto3` (не minio SDK), обёрнут в `admin/app/storage.py`. Функция `get_minio_client()` создаёт `boto3.client('s3', ...)`.
- **БД-таблицы** создаются автоматически при старте admin через `Base.metadata.create_all`. Alembic настроен (`admin/alembic/`) с одной миграцией `001_create_kb_tables.py`.
- **Legacy**: `admin/knowledge/` монтируется read-only для seed-скрипта. Директория больше не является источником данных — файлы хранятся в MinIO.
- Ollama-контейнер использует кастомный entrypoint (`admin/scripts/ollama-entrypoint.sh`): стартует `ollama serve` в фоне → подтягивает модели → `wait`.
- **Admin-сервис**: роутер в `app/router.py` (prefix `/api/v1/knowledge-base`), бизнес-логика в `app/service.py` (`KnowledgeBaseService` принимает SQLAlchemy `Session`), модели БД в `app/db_models.py`, Pydantic-схемы в `app/schemas.py`.
- **Admin-frontend**: API-обёртка в `admin-frontend/src/api.ts` (типы `KBVersion`/`KBFile` дублируют Pydantic-схемы admin — при изменении `schemas.py` синхронизировать оба). UI-компоненты в `src/components/` (модалки загрузки/активации/списка, таблица версий).
- **Query-widget**: одиночный компонент `App.tsx` с состоянием чата в React state (без персистентности). Обрабатывает три класса ошибок: сеть недоступна, HTTP не-200, прочие исключения — у каждой свой русский текст.
- Backend Dockerfiles: `python:3.12-slim`, `uv` из `ghcr.io/astral-sh/uv:latest`, установка через `uv sync --no-dev`. Frontend Dockerfiles: multi-stage (`node:20/22-alpine` build → `nginx:alpine` serve).
