import json
import os
from typing import Optional, Tuple

from app.db.base import SessionLocal
from app.models.document import Document
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreManager
from app.services.structured_data_processor import process_structured
from app.workers.celery_app import celery_app
from app.core.logging import get_logger


logger = get_logger(__name__)


def _ingest_and_index_sync(
    *,
    file_path: str,
    file_type: str,
    vector_store_name: str,
    org_vector_dir: str,
    org_structured_dir: str,
) -> Tuple[Optional[str], str, int]:
    """
    Synchronous ingestion/indexing for Celery worker.

    Returns: (sqlite_path, vector_store_path, chunk_count)
    """
    document_processor = DocumentProcessor()
    vector_store_manager = VectorStoreManager()

    structured_types = {"csv", "xlsx", "xls", "db", "sqlite"}

    if file_type in structured_types:
        sqlite_path, documents = process_structured(
            file_path,
            file_type,
            vector_store_name,
            output_dir=str(org_structured_dir),
        )
        chunk_count = len(documents)
        if chunk_count == 0:
            if sqlite_path and os.path.exists(sqlite_path):
                os.remove(sqlite_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            raise ValueError("Structured file could not be processed or is empty")

        vector_store_path = vector_store_manager.create_vector_store(
            documents,
            vector_store_name,
            base_dir=str(org_vector_dir),
        )
        return sqlite_path, vector_store_path, chunk_count

    # Unstructured: RAG-only via FAISS
    documents = document_processor.process_document(file_path, file_type)
    chunk_count = len(documents)
    if chunk_count == 0:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise ValueError("Document could not be processed or is empty")

    vector_store_path = vector_store_manager.create_vector_store(
        documents,
        vector_store_name,
        base_dir=str(org_vector_dir),
    )
    return None, vector_store_path, chunk_count


@celery_app.task(name="tasks.ingest_document", bind=True)
def ingest_document_task(
    self,
    *,
    document_id: int,
    organization_id: int,
    file_path: str,
    file_type: str,
    vector_store_name: str,
    org_vector_dir: str,
    org_structured_dir: str,
) -> None:
    """Celery task: ingest an uploaded document and update its indexing fields."""
    session = SessionLocal()
    doc = None
    try:
        doc = session.query(Document).filter(Document.id == document_id).one_or_none()
        if not doc:
            return

        # Defense-in-depth: ensure the worker is only ingesting within the expected org.
        if getattr(doc, "organization_id", None) != organization_id:
            return

        sqlite_path, vector_store_path, chunk_count = _ingest_and_index_sync(
            file_path=file_path,
            file_type=file_type,
            vector_store_name=vector_store_name,
            org_vector_dir=org_vector_dir,
            org_structured_dir=org_structured_dir,
        )

        doc.vector_store_path = vector_store_path
        doc.chunk_count = chunk_count
        doc.sqlite_path = sqlite_path
        doc.extra_metadata = json.dumps({"ingestion_status": "ready", "error": None})
        session.add(doc)
        session.commit()

    except Exception as e:
        logger.exception("ingestion_failed", extra={"document_id": document_id})
        if doc is None:
            doc = session.query(Document).filter(Document.id == document_id).one_or_none()
        if doc is not None:
            doc.chunk_count = 0
            doc.extra_metadata = json.dumps(
                {"ingestion_status": "failed", "error": str(e)}
            )
            session.add(doc)
            session.commit()
        # Re-raise so the task is marked as failed (and can be configured to retry).
        raise
    finally:
        session.close()

