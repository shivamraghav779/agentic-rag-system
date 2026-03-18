"""Document service layer."""
import os
import asyncio
import json
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.artifact_paths import (
    get_organization_structured_data_dir,
    get_organization_upload_dir,
    get_organization_vector_store_dir,
)
from app.crud.document import document as document_crud
from app.crud.organization import organization as organization_crud
from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.document import UploadResponse
from app.schemas.document import IngestionStatusResponse
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreManager
from app.services.structured_data_processor import process_structured

# File types that use hybrid SQL + RAG pipeline (orchestrator)
STRUCTURED_FILE_TYPES = frozenset({"csv", "xlsx", "xls", "db", "sqlite"})
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for document operations."""

    def __init__(
        self,
        db: AsyncSession,
        document_processor: Optional[DocumentProcessor] = None,
        vector_store_manager: Optional[VectorStoreManager] = None,
    ):
        """Initialize document service with database session."""
        self.db = db
        self.document_crud = document_crud
        self.organization_crud = organization_crud
        self.document_processor = document_processor or DocumentProcessor()
        self.vector_store_manager = vector_store_manager or VectorStoreManager()
    
    async def upload_document(
        self,
        file: UploadFile,
        user: User,
        organization_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> UploadResponse:
        """
        Upload and process a document.
        
        Args:
            file: Uploaded file
            user: Current user
            organization_id: Organization ID (defaults to user's organization)
            category: Document category
            
        Returns:
            Upload response with document info
            
        Raises:
            HTTPException: If user cannot upload or processing fails
        """
        # Validate user can upload
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be assigned to an organization to upload documents. Private users cannot upload documents."
            )
        
        # Determine organization_id
        if organization_id is None:
            organization_id = user.organization_id
        else:
            # Verify user can access this organization
            if not user.can_access_organization(organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        
        # Verify organization exists
        org = await self.organization_crud.get(self.db, id=organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Validate file type
        file_type = self._validate_file_type(file)
        
        try:
            file_id = str(uuid.uuid4())
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing filename in upload",
                )

            file_extension = Path(file.filename).suffix.lower()
            if not file_extension or len(file_extension) > 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported or invalid file extension",
                )

            # Basic extension sanitization (prevents odd characters in paths).
            # We only keep alnum and '.' from the suffix.
            ext_clean = "".join(ch for ch in file_extension if ch.isalnum() or ch == ".")
            if ext_clean != file_extension:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file extension format",
                )

            safe_filename = f"{file_id}{file_extension}"
            # Per-org layout: artifacts/{org_id}/uploads|vector_store|structured_data
            org_upload_dir = get_organization_upload_dir(organization_id)
            file_path = str(org_upload_dir / safe_filename)

            # Enforce upload size limit before reading the full payload into memory.
            # UploadFile.size is not always available depending on the client/proxy.
            max_read = settings.max_file_size + 1
            content = await file.read(max_read)
            if len(content) > settings.max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Max allowed size is {settings.max_file_size} bytes.",
                )
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            file_size = len(content)
            vector_store_name = f"doc_{file_id}"
            org_vector_dir = get_organization_vector_store_dir(organization_id)
            org_structured_dir = get_organization_structured_data_dir(organization_id)

            # Pre-compute target paths and create the DB record immediately.
            # Ingestion/indexing happens in the background so uploads don't
            # block on embedding/index creation.
            vector_store_path = str(org_vector_dir / vector_store_name)
            sqlite_path = None
            if file_type in STRUCTURED_FILE_TYPES:
                sqlite_path = str(Path(org_structured_dir) / f"{vector_store_name}.db")

            document_dict = {
                "user_id": user.id,
                "organization_id": organization_id,
                "filename": file.filename,
                "file_type": file_type,
                "file_path": file_path,
                "vector_store_path": vector_store_path,
                "file_size": file_size,
                "chunk_count": 0,  # not ready yet; set after ingestion
                "category": category,
                "version": 1,
                "extra_metadata": json.dumps(
                    {"ingestion_status": "processing", "error": None}
                ),
            }
            if sqlite_path is not None:
                document_dict["sqlite_path"] = sqlite_path

            db_document = await self.document_crud.create_from_dict(self.db, obj_dict=document_dict)

            # Kick off ingestion/indexing in the background.
            # If this fails, the document remains with chunk_count=0.
            if settings.enable_celery_tasks:
                from app.tasks.document_tasks import ingest_document_task

                try:
                    ingest_document_task.delay(
                        document_id=db_document.id,
                    organization_id=organization_id,
                        file_path=file_path,
                        file_type=file_type,
                        vector_store_name=vector_store_name,
                        org_vector_dir=str(org_vector_dir),
                        org_structured_dir=str(org_structured_dir),
                    )
                except Exception:
                    # If broker/Redis is down, fall back so uploads don't get stuck.
                    asyncio.create_task(
                        self._background_ingest_document(
                            document_id=db_document.id,
                            organization_id=organization_id,
                            file_path=file_path,
                            file_type=file_type,
                            vector_store_name=vector_store_name,
                            org_vector_dir=str(org_vector_dir),
                            org_structured_dir=str(org_structured_dir),
                        )
                    )
            else:
                # Fallback: non-durable background job (useful for local dev).
                asyncio.create_task(
                    self._background_ingest_document(
                        document_id=db_document.id,
                        organization_id=organization_id,
                        file_path=file_path,
                        file_type=file_type,
                        vector_store_name=vector_store_name,
                        org_vector_dir=str(org_vector_dir),
                        org_structured_dir=str(org_structured_dir),
                    )
                )

            return UploadResponse(
                document_id=db_document.id,
                filename=file.filename,
                message="Document uploaded. Ingestion is running; chat will be available after indexing completes.",
                chunk_count=0,
            )
        
        except HTTPException:
            raise
        except Exception as e:
            # Clean up on error
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            
            # Provide more user-friendly error messages
            error_message = str(e)
            if "api key" in error_message.lower() or "api_key" in error_message.lower():
                if "expired" in error_message.lower() or "invalid" in error_message.lower():
                    detail = "API key expired or invalid. Please contact the administrator to renew the API keys."
                else:
                    detail = f"API key error: {error_message}"
            elif "vector store" in error_message.lower():
                detail = f"Error creating document embeddings: {error_message}"
            else:
                detail = f"Error processing document: {error_message}"
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail
            )
    
    async def list_documents(
        self,
        user: User,
        organization_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[Document]:
        """
        List documents accessible by user.
        
        Args:
            user: Current user
            organization_id: Optional organization filter
            category: Optional category filter
            
        Returns:
            List of documents
        """
        # Private users cannot see documents
        if not user.is_organization_user():
            return []
        
        # If organization_id specified, verify access
        if organization_id is not None:
            if not user.can_access_organization(organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
            return await self.document_crud.get_by_organization(
                self.db,
                organization_id=organization_id,
                category=category,
                user=user
            )

        # Get user's organization documents
        if user.organization_id:
            return await self.document_crud.get_by_organization(
                self.db,
                organization_id=user.organization_id,
                category=category,
                user=user
            )
        
        return []
    
    async def get_document(self, document_id: int, user: User) -> Document:
        """
        Get a specific document.
        
        Args:
            document_id: Document ID
            user: Current user
            
        Returns:
            Document
            
        Raises:
            HTTPException: If document not found or access denied
        """
        # Private users cannot access documents
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot access documents. You must be part of an organization."
            )
        
        document = await self.document_crud.get(self.db, id=document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        if not self.document_crud.can_access(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )
        return document

    async def get_ingestion_status(self, document_id: int, user: User) -> IngestionStatusResponse:
        """Return ingestion/indexing status for a given document."""
        document = await self.get_document(document_id=document_id, user=user)

        ingestion_status = "unknown"
        error: Optional[str] = None
        extra = getattr(document, "extra_metadata", None)
        if extra:
            try:
                parsed = json.loads(extra)
                ingestion_status = parsed.get("ingestion_status") or ingestion_status
                err = parsed.get("error")
                if isinstance(err, str) and err.strip():
                    error = err.strip()
            except Exception:
                # If metadata is malformed, keep defaults.
                pass

        return IngestionStatusResponse(
            document_id=document.id,
            ingestion_status=ingestion_status,
            error=error,
            chunk_count=getattr(document, "chunk_count", 0) or 0,
        )

    async def delete_document(self, document_id: int, user: User) -> None:
        """
        Delete a document.
        
        Args:
            document_id: Document ID
            user: Current user
            
        Raises:
            HTTPException: If document not found or access denied
        """
        # Private users cannot delete documents
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot delete documents. You must be part of an organization."
            )
        
        document = await self.document_crud.get(self.db, id=document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        if not self.document_crud.can_access(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )
        
        # Check delete permissions
        if not self.document_crud.can_delete(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to delete this document"
            )
        
        try:
            vector_store_path = document.vector_store_path
            file_path = document.file_path
            sqlite_path = getattr(document, "sqlite_path", None)

            await self.document_crud.delete(self.db, id=document_id)

            try:
                if vector_store_path:
                    self.vector_store_manager.delete_vector_store(vector_store_path)
            except Exception as e:
                print(f"Warning: Could not delete vector store at {vector_store_path}: {str(e)}")

            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete file at {file_path}: {str(e)}")

            if sqlite_path and os.path.exists(sqlite_path):
                try:
                    os.remove(sqlite_path)
                except Exception as e:
                    print(f"Warning: Could not delete SQLite at {sqlite_path}: {str(e)}")
        
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting document: {str(e)}"
            )
    
    def _validate_file_type(self, file: UploadFile) -> str:
        """
        Validate and determine file type.
        Supported: PDF, DOCX, TXT, HTML, MD, Excel (xlsx/xls), CSV, SQLite (db/sqlite).
        """
        allowed_mime = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "text/plain": "txt",
            "text/html": "html",
            "text/csv": "csv",
            "application/vnd.ms-excel": "xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/octet-stream": None,  # infer from extension
        }
        file_type = allowed_mime.get(file.content_type)
        if not file_type:
            filename_lower = (file.filename or "").lower()
            if filename_lower.endswith(".pdf"):
                file_type = "pdf"
            elif filename_lower.endswith((".docx", ".doc")):
                file_type = "docx"
            elif filename_lower.endswith(".txt"):
                file_type = "txt"
            elif filename_lower.endswith((".html", ".htm")):
                file_type = "html"
            elif filename_lower.endswith((".md", ".markdown")):
                file_type = "md"
            elif filename_lower.endswith(".csv"):
                file_type = "csv"
            elif filename_lower.endswith(".xlsx"):
                file_type = "xlsx"
            elif filename_lower.endswith(".xls"):
                file_type = "xls"
            elif filename_lower.endswith((".db", ".sqlite", ".sqlite3")):
                file_type = "db"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported file type. Supported: PDF, DOCX, TXT, HTML, MD, Excel (xlsx/xls), CSV, SQLite (db/sqlite)",
                )
        return file_type

    async def _background_ingest_document(
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
        """Background ingestion/indexing job for an uploaded document."""
        # Import here to avoid circular imports during startup.
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            try:
                sqlite_path, vector_store_path, chunk_count = await asyncio.to_thread(
                    self._ingest_and_index_document_sync,
                    file_path=file_path,
                    file_type=file_type,
                    vector_store_name=vector_store_name,
                    org_vector_dir=org_vector_dir,
                    org_structured_dir=org_structured_dir,
                )

                doc = await self.document_crud.get(session, id=document_id)
                if not doc:
                    return

                # Defense-in-depth: only ingest within the expected org.
                if getattr(doc, "organization_id", None) != organization_id:
                    return

                doc.vector_store_path = vector_store_path
                doc.chunk_count = chunk_count
                doc.sqlite_path = sqlite_path
                doc.extra_metadata = json.dumps(
                    {"ingestion_status": "ready", "error": None}
                )
                session.add(doc)
                await session.commit()
            except HTTPException as exc:
                doc = await self.document_crud.get(session, id=document_id)
                if doc:
                    doc.chunk_count = 0
                    doc.extra_metadata = json.dumps(
                        {"ingestion_status": "failed", "error": exc.detail}
                    )
                    session.add(doc)
                    await session.commit()
                logger.warning(
                    "ingestion_failed",
                    extra={"document_id": document_id, "detail": exc.detail},
                )
            except Exception as e:
                doc = await self.document_crud.get(session, id=document_id)
                if doc:
                    doc.chunk_count = 0
                    doc.extra_metadata = json.dumps(
                        {"ingestion_status": "failed", "error": str(e)}
                    )
                    session.add(doc)
                    await session.commit()
                logger.exception(
                    "ingestion_failed",
                    extra={"document_id": document_id},
                )

    def _ingest_and_index_document_sync(
        self,
        *,
        file_path: str,
        file_type: str,
        vector_store_name: str,
        org_vector_dir: str,
        org_structured_dir: str,
    ):
        """
        Synchronous ingestion + indexing.

        Runs in a worker thread via `asyncio.to_thread(...)`.
        Returns: (sqlite_path, vector_store_path, chunk_count)
        """
        sqlite_path = None
        if file_type in STRUCTURED_FILE_TYPES:
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
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Structured file could not be processed or is empty",
                )

            vector_store_path = self.vector_store_manager.create_vector_store(
                documents,
                vector_store_name,
                base_dir=str(org_vector_dir),
            )
            return sqlite_path, vector_store_path, chunk_count

        # Unstructured: RAG-only via FAISS
        documents = self.document_processor.process_document(file_path, file_type)
        chunk_count = len(documents)
        if chunk_count == 0:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document could not be processed or is empty",
            )

        vector_store_path = self.vector_store_manager.create_vector_store(
            documents,
            vector_store_name,
            base_dir=str(org_vector_dir),
        )
        return sqlite_path, vector_store_path, chunk_count

