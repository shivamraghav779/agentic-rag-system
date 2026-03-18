# Agentic RAG System

## Project Overview
TechTattava Chatbot Backend is a secure, multi-tenant RAG-based document chatbot.
Organizations can upload documents, a background ingestion pipeline chunks/embeds them into a per-organization FAISS vector store, and users can chat with those documents via retrieval + grounding verification.

Key highlights:
- Multi-tenant authorization (OrgAdmin/OrgUser/Private User roles)
- Async ingestion via `Celery` + `Redis` (with ingestion status tracking)
- Document-grounded chat via RAG (Gemini/Groq provider fallback)
- Rate limiting + structured JSON logs + global exception handling

## Documentation (source of truth)
- `PROJECT_ARCHITECTURE.md` - layered code architecture + component diagram
- `SYSTEM_DESIGN_DOCUMENT.md` - end-to-end runtime flow (upload -> background ingestion -> RAG chat) + API cheat sheet

API docs (when running):
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Quick Start (local)
1. Configure environment
   - Copy `.env.example` to `.env`
2. Database
   - Run migrations: `./scripts/run_migrations.sh upgrade`
3. Start background ingestion (Celery)
   - Run Redis first (broker/backend)
   - Start worker (from repo root): `celery -A app.workers.celery_app.celery_app worker --loglevel=INFO`
4. Start API server
   - `uvicorn main:app --host 0.0.0.0 --port 8000`

## Handy Endpoints
- Health: `GET /health`
- Upload document: `POST /api/v1/documents/upload`
- Ingestion status: `GET /api/v1/documents/{document_id}/ingestion-status`
- Chat: `POST /api/v1/chat`
- Chat stream: `POST /api/v1/chat/stream`

