# RAG Prototype

Локальная RAG-система (Retrieval-Augmented Generation) для ответов на вопросы по содержимому файла `info.md`.

## Архитектура

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│ FastAPI  │────▶│  Qdrant │     │ Ollama  │
│  :8000   │     │  :6333  │     │ :11434  │
│          │────▶│ vectors │     │ bge-m3  │
│  /ask    │     └─────────┘     │qwen2.5  │
│ /ingest  │────────────────────▶│         │
└─────────┘                      └─────────┘
```

**Поток данных:**
1. **Ingestion**: `info.md` → chunking (300 символов, overlap 100) → embeddings (bge-m3) → Qdrant
2. **Query**: вопрос → embedding → поиск в Qdrant → контекст + промпт → Qwen 2.5 → ответ

## Запуск

```bash
docker-compose up --build
```

При первом запуске Ollama автоматически скачает модели (~5 ГБ). Дождитесь сообщения `All models are ready.` в логах.

## API

### POST /ask

Задать вопрос:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Кто является генеральным директором?"}'
```

Ответ:
```json
{"answer": "Генеральный директор компании ТехноСтарт — Алексей Петров."}
```

Если ответа нет в базе знаний:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Какая погода в Лондоне?"}'
```

```json
{"answer": "Информация не найдена"}
```

### POST /ingest

Принудительно перечитать `info.md` и обновить векторную базу:

```bash
curl -X POST http://localhost:8000/ingest
```

```json
{"status": "ok", "chunks_count": 7}
```

## Стек

- **Backend**: Python 3.12, FastAPI, LangChain
- **Vector DB**: Qdrant (cosine similarity)
- **LLM**: Qwen 2.5 7B (via Ollama)
- **Embeddings**: BGE-M3 (via Ollama)
- **Package Manager**: uv
