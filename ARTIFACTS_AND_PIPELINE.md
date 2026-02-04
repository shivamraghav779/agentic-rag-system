# Artifacts Layout and Chatbot Pipeline

## Per-Organization Artifact Layout

All file-based artifacts (vector stores, structured data, uploads) are stored **per organization** under a single root:

```
artifacts/
  {organization_id}/
    uploads/           # Raw uploaded files (PDF, DOCX, Excel, CSV, etc.)
    vector_store/      # FAISS vector indexes (one folder per document, e.g. doc_<uuid>)
    structured_data/   # SQLite databases from Excel/CSV/DB uploads (e.g. doc_<uuid>.db)
```

- **Config**: `ARTIFACTS_BASE_DIR` (default `./artifacts`) in `.env`.
- **Helpers**: `app/core/artifact_paths.py` — `get_organization_upload_dir()`, `get_organization_vector_store_dir()`, `get_organization_structured_data_dir()`, `delete_organization_artifacts()`.
- **Organization delete**: Deleting an organization removes `artifacts/{organization_id}/` and all contents (cascade-deleted documents no longer have files on disk).

Existing documents that were created before this layout may still have paths under the legacy `vector_stores/`, `sqlite_stores/`, or `uploads/`; those paths continue to work. New uploads use the per-org layout.

---

## End-to-End Pipeline

### 1. Upload

| File type | Flow | Where it goes |
|-----------|------|----------------|
| **Unstructured** (PDF, DOCX, TXT, HTML, MD) | File → DocumentProcessor (chunk) → FAISS vector store | `artifacts/{org_id}/uploads/`, `artifacts/{org_id}/vector_store/doc_<uuid>/` |
| **Structured** (Excel, CSV, SQLite) | File → StructuredDataProcessor (SQLite + row docs) → FAISS | `artifacts/{org_id}/uploads/`, `artifacts/{org_id}/structured_data/doc_<uuid>.db`, `artifacts/{org_id}/vector_store/doc_<uuid>/` |

- Upload endpoint validates file type and organization access, then calls `DocumentService.upload_document()`.
- Document record stores: `file_path`, `vector_store_path`, and optionally `sqlite_path` (for structured).

### 2. Chat (Query)

| Document type | Pipeline |
|---------------|----------|
| **Unstructured** (no `sqlite_path`) | RAG only: query rewrite/expansion → similarity search → rerank → optional prompt compression → LLM. |
| **Structured** (has `sqlite_path`) | **Orchestrator**: classify query (SQL vs RAG) → either SQL Agent on `sqlite_path` or same RAG chain on `vector_store_path`. |

- Chat uses `document.vector_store_path` and, when present, `document.sqlite_path` (paths may be under `artifacts/{org_id}/...` or legacy dirs).
- Document delete removes the document row and then deletes the files at the stored paths (vector store, upload file, sqlite if any).

### 3. Robustness Checklist (what’s in place and what to consider)

**Already in place**

- Per-org isolation: each org’s artifacts live under `artifacts/{org_id}/`.
- Organization delete cleans up `artifacts/{org_id}/`.
- Document delete removes vector store, upload file, and SQLite file when present.
- Structured pipeline: Excel/CSV/DB → SQLite + row-level docs for RAG; orchestrator routes SQL vs RAG.
- RAG enhancements: query rewrite/expansion, reranking, optional prompt compression.
- Multi-provider LLM fallback (Gemini → Groq) and multi-key rotation.

**Suggestions for extra robustness**

1. **Upload size and timeouts**  
   - Enforce max file size (e.g. FastAPI dependency or nginx) and consider longer timeouts for large Excel/PDF uploads.

2. **Structured data limits**  
   - For very large Excel/CSV, consider chunking row-docs or sampling for RAG to avoid huge vector stores and timeouts; optionally cap rows per sheet or per file in `structured_data_processor`.

3. **SQL agent safety**  
   - SQL agent runs generated SQL read-only where possible (e.g. read-only DB connection or SQLite `?mode=ro`); already using a dedicated SQLite file per document.

4. **Idempotent / retries**  
   - Upload is not idempotent (new UUID each time). For critical flows, consider idempotency keys or “replace document” by external id.

5. **Health and artifact disk usage**  
   - Optional health endpoint that checks `artifacts_base_dir` exists and is writable; optional background job to report disk usage per org.

6. **Backup and restore**  
   - Back up `artifacts/` (and DB) together; document paths in DB are relative or absolute to this server, so restore to the same path or document a path-migration process.

7. **Legacy paths**  
   - Documents created before per-org layout still reference `vector_stores/`, `sqlite_stores/`, or `uploads/`. Keep those dirs writable/readable until you migrate or drop support.

8. **Concurrency**  
   - FAISS and SQLite per document reduce cross-request contention; ensure no single org can exhaust CPU/memory (e.g. very large or many concurrent uploads) if needed.

---

## Quick Reference

| Concern | Location |
|--------|----------|
| Artifact paths | `app/core/artifact_paths.py`, `app/core/config.py` (artifacts_base_dir) |
| Upload flow | `app/services/document_service.py` (upload_document) |
| Unstructured processing | `app/services/document_processor.py` |
| Structured processing | `app/services/structured_data_processor.py` |
| Vector store | `app/services/vector_store.py` |
| RAG + enhancements | `app/services/rag_chain.py`, `app/services/rag_enhancements.py` |
| SQL + orchestrator | `app/services/sql_agent_service.py`, `app/services/query_orchestrator.py` |
| Chat entry | `app/services/chat_service.py` (chat_with_document) |
| Org delete cleanup | `app/services/organization_service.py` (delete_organization) |
