# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack educational RAG (Retrieval-Augmented Generation) Q&A system with a FastAPI backend and React frontend. The backend integrates vector search (Milvus), BM25 keyword search, MySQL for persistence, Redis for caching, and an LLM (DashScope/Alibaba Cloud or compatible OpenAI-format API).

## Running the Project

**Backend** (from `integerate_qa_system/`):
```bash
cd integerate_qa_system
uvicorn api:app --reload --port 8000
```

**Frontend** (from `rag-frontend/`):
```bash
npm run dev        # dev server at http://localhost:5173
npm run build      # production build
npm run lint       # ESLint
npm run preview    # preview production build
```

No test suite is configured.

## Configuration

All backend config lives in `integerate_qa_system/config.ini`. Required sections:
- `[mysql]` — host, user, password, database
- `[redis]` — host, port, password, db
- `[milvus]` — host, port, database_name, collection_name
- `[llm]` — model, api_key, base_url (OpenAI-compatible; defaults to DashScope)
- `[email]` — qq_email, qq_auth_code for login verification codes
- `[jwt]` — secret_key, algorithm, expire_days
- `[retrieval]` — chunk sizes, retrieval_k, candidate_m
- `[app]` — valid_sources, customer_service_phone

`Config` is a singleton (`base/config.py`). LLM, retrieval, app, email, and JWT settings support **hot-reload** via `Config.hot_reload()` without restarting the server. MySQL, Redis, Milvus, and logger settings are **not** hot-reloadable.

Thinking models (deepseek-reasoner, qwen3, etc.) are auto-detected by model name — see `THINKING_MODELS` list in `base/config.py`.

## Backend Architecture

```
integerate_qa_system/
├── api.py               # FastAPI app, all HTTP endpoints, CORS config
├── new_main.py          # IntegratedQASystem — top-level orchestrator
├── config.ini           # All runtime configuration
├── base/
│   ├── config.py        # Config singleton with hot-reload
│   ├── logger.py        # Shared logger
│   └── trace_models.py  # Trace data models for pipeline observability
├── login/
│   ├── auth.py          # JWT auth, AuthService
│   └── email_service.py # Email verification code via QQ SMTP
├── mysql_qa/
│   ├── db/mysql_client.py       # MysqlClient — all DB operations
│   ├── cache/redis_client.py    # RedisClient
│   └── retrieval/bm25_search.py # BM25Search
└── rag_qa/
    ├── core/
    │   ├── vector_store.py       # VectorStore (Milvus hybrid search + rerank)
    │   ├── new_rag_system.py     # RAGSystem — main RAG pipeline
    │   ├── query_classifier.py   # BERT-based query classifier
    │   ├── strategy_selector.py  # Retrieval strategy selection
    │   ├── document_process.py   # Document ingestion pipeline
    │   └── prompts.py            # All LLM prompt templates
    └── edu_document_loaders/     # PDF, DOCX, PPT, image loaders
```

**Request flow:** `api.py` → `IntegratedQASystem.answer()` → `RAGSystem.generate()` → query classify → strategy select → hybrid vector+BM25 search → rerank → LLM stream generation. Each step is recorded in `TraceData` and stored in the `conversations` table's `trace_data` field.

## Frontend Architecture

```
rag-frontend/src/
├── App.jsx        # Root: auth gate, mode switching, layout
├── api.js         # All Axios calls to http://localhost:8000
└── components/
    ├── SidebarModern.jsx   # Session list, mode/tab switcher, user info
    ├── ChatAreaModern.jsx  # QA mode chat with streaming support
    ├── KnowledgePage.jsx   # Knowledge base file management
    ├── ConfigPage.jsx      # System config hot-reload UI
    ├── FqaPage.jsx         # FAQ management
    └── CasePage.jsx        # Case analysis
```

The app has two top-level modes (stored in `localStorage`):
- **QA mode** (`mode === 'qa'`): chat interface with session history
- **Professional mode**: four tabs — knowledge, config, fqa, case

Auth uses JWT stored in `localStorage`. Token is verified against the backend on every page load.

Streaming responses from the backend are consumed via `fetch` with chunked reading (not Axios) in `ChatAreaModern`.
