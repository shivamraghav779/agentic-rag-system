# System Design Document

## 1. Purpose
This document describes the end-to-end behavior of the Private Document Chatbot system:
upload -> background ingestion -> per-organization indexing -> RAG chat -> persistence.

It is intentionally paired with `PROJECT_ARCHITECTURE.md`, which explains the layered code organization.

## 2. High-Level Runtime Flow

### 2.1 Document Upload & Ingestion (Async)
1. Client uploads a file to `POST /api/v1/documents/upload` with `Authorization: Bearer <access_token>`.
2. `DocumentService.upload_document()`:
   - validates file type + size
   - stores the raw file under `artifacts/{organization_id}/uploads/`
   - creates a `documents` DB row with:
     - `organization_id`
     - `vector_store_path` (target path)
     - `chunk_count = 0` (not ready yet)
     - `extra_metadata.ingestion_status = "processing"`
3. Background indexing is enqueued:
   - Celery worker + Redis broker (recommended for durability)
4. Worker runs `ingest_document_task`:
   - re-reads the `documents` row
   - verifies `doc.organization_id == organization_id` (defense-in-depth)
   - processes the file into LangChain `Document` chunks
   - builds embeddings
   - writes FAISS index to `artifacts/{organization_id}/vector_store/`
   - updates:
     - `documents.chunk_count`
     - `documents.sqlite_path` for structured docs
     - `documents.extra_metadata.ingestion_status = "ready"`

### 2.2 Chat with a Document (Multi-Agent + RAG)
1. Client sends:
   - `POST /api/v1/chat` or `POST /api/v1/chat/stream`
2. `ChatService.chat_with_document()`:
   - verifies the user is an organization user
   - enforces chat limits (daily, per user)
   - checks the document is accessible and ingestion is complete (`chunk_count > 0`)
3. Router agent selects route:
   - `retrieval`: use `RetrievalAgent` (RAG pipeline)
   - `tool`: use `ToolAgent`
   - `general`: use `GeneralAgent` for direct LLM answer
4. Retrieval path (`RetrievalAgent`) delegates to existing stack:
   - `QueryOrchestrator` for structured docs (`sqlite_path`)
   - `RAGChain.query()` for unstructured docs
   - includes rewrite/expansion, retrieval, reranking, prompt compression, grounding verification
5. Tool path (`ToolAgent`) supports:
   - calculator tool (safe arithmetic)
   - DB tool (`how many documents` in current organization)
   - document-search tool (calls RetrievalAgent/RAG as tool)
6. Optional response cache:
   - key: `organization_id + document_id + route + normalized_query`
   - TTL controlled by settings
7. Persist chat history:
   - stores question/answer + token usage in `chat_history`
   - updates `conversation.updated_at` and `user.used_tokens`

### 2.3 Multi-Agent Runtime Controls
- `ENABLE_MULTI_AGENT_ROUTING=true|false`
  - `false` forces retrieval-only behavior (safe fallback mode)
- `ENABLE_AGENT_RESPONSE_CACHE=true|false`
- `AGENT_RESPONSE_CACHE_TTL_SECONDS=...`

## 3. Multi-Tenancy & Data Isolation

### 3.1 Role Model (as enforced by code)
- `SuperAdmin` and `Admin`: broader platform access.
- `OrgAdmin` and `OrgUser`: scoped to `user.organization_id`.
- `Private User` (`UserRole.USER`): currently **cannot upload documents or chat with documents** in this codebase.

### 3.2 Isolation Rules (MUST enforce in design)
- **Documents and vectors are per organization**:
  - raw files: `artifacts/{organization_id}/uploads/`
  - FAISS indexes: `artifacts/{organization_id}/vector_store/`
  - structured SQLite: `artifacts/{organization_id}/structured_data/`
- **Chat uses only the `document.vector_store_path` that belongs to the document row**.
- **Chat history access is scoped by `user_id`** (and chat endpoints validate document ownership).
- **Celery ingestion is org-verified**:
  - worker checks `doc.organization_id` against the task’s `organization_id`.

## 4. Security Overview

### 4.1 Authentication
- JWT access token + refresh token.
- Password hashing: Argon2 (via `passlib[argon2]`).

### 4.2 Authorization
- Every document-related action enforces:
  - `user.can_access_organization(document.organization_id)`
  - and appropriate role checks.

### 4.3 Input & File Validation
- File validation includes:
  - allowed extensions / content types
  - upload size limit (`MAX_FILE_SIZE`)
  - per-org safe filenames using UUIDs

### 4.4 Rate Limiting
- Middleware applies to:
  - `POST /api/v1/chat`
  - `POST /api/v1/chat/stream`
- Additionally, `ChatService` enforces a per-user daily `chat_limit`.

### 4.5 Guardrails against hallucination
- A verifier model checks if the final answer is supported by retrieved context.
- If it cannot verify support, the system returns a refusal-style response.

## 5. Observability & Operations

- Structured logging: JSON logs with `request_id`.
- Chat service logs include:
  - selected agent route
  - query snippet
  - response duration
- Global exception handling middleware:
  - SQLAlchemy errors -> safe 5xx JSON
  - LLM/Gemini/Groq errors -> mapped HTTP status codes
- Health endpoint:
  - `GET /health` checks DB connectivity.

## 6. API Surface (Endpoint Cheat Sheet)

Base: `/api/v1`

### Auth
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `PATCH /auth/me/system-prompt`

### Documents
- `POST /documents/upload?organization_id=&category=`
- `GET /documents?organization_id=&category=`
- `GET /documents/{document_id}`
- `DELETE /documents/{document_id}`
- `GET /documents/{document_id}/ingestion-status`

### Chat
- `POST /chat` (JSON response)
- `POST /chat/stream` (SSE stream of deltas + final payload)
- `GET /chat/history?document_id=&conversation_id=`
- `GET /chat/history/{chat_id}`
- `POST /chat/conversations`
- `GET /chat/conversations?document_id=`
- `GET /chat/conversations/{conversation_id}`
- `PATCH /chat/conversations/{conversation_id}`
- `DELETE /chat/conversations/{conversation_id}`

### Analytics
- `GET /statistics/user`
- `GET /statistics/organization/{organization_id}`
- `GET /statistics/admin`

### Admin
- `GET/POST /admin/superadmins`
- `GET/POST /admin/admins`

## 7. Deployment (Minimal)
1. Create `.env` from `.env.example`.
2. Run migrations: `alembic upgrade head`
3. Start Redis (for Celery): default `redis://localhost:6379/0`
4. Start Celery worker (recommended):
   - `celery -A app.workers.celery_app.celery_app worker --loglevel=INFO`
5. Start API server:
   - `uvicorn main:app --host 0.0.0.0 --port 8000`

## 8. Assumptions / Known Constraints
- This codebase does not currently support true token-level streaming from the provider; `/chat/stream` streams the final answer in smaller server-side chunks.
- Private users are not allowed to upload/chat documents in the current authorization rules.

