"""Document processing module for various file types using Langchain loaders."""
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    TextLoader,
    BSHTMLLoader,
)
from app.core.config import settings

# Markdown: use TextLoader (MD is plain text) for simplicity; optional UnstructuredMarkdownLoader if needed
try:
    from langchain_community.document_loaders import UnstructuredMarkdownLoader
    _MD_LOADER = "unstructured"
except ImportError:
    _MD_LOADER = "text"


class DocumentProcessor:
    """Processes various document types using Langchain loaders and splits them into chunks."""
    
    def __init__(self):
        strategy = (settings.chunking_strategy or "recursive").lower()

        # A poor chunking setup yields many tiny fragments which hurts retrieval.
        # We keep the strategy configurable and enforce min/max guardrails below.
        if strategy == "character":
            self.text_splitter = CharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                length_function=len,
            )
        else:
            # Default: recursive/paragraph-aware splitting
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                length_function=len,
            )

    def _split_and_filter(self, documents: List[Document], *, doc_type: str, source: str) -> List[Document]:
        """Split into chunks and filter unusable tiny chunks."""
        raw_chunks = self.text_splitter.split_documents(documents)

        min_len = max(0, settings.min_chunk_size_chars)
        chunks: List[Document] = []
        for c in raw_chunks:
            text = getattr(c, "page_content", "") or ""
            if not text or not text.strip():
                continue
            if len(text) < min_len:
                continue
            chunks.append(c)

        # Cap chunk count per document to avoid runaway ingestion cost.
        if settings.max_chunks_per_document and len(chunks) > settings.max_chunks_per_document:
            chunks = chunks[: settings.max_chunks_per_document]

        for i, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "chunk_id": i,
                    "type": doc_type,
                    "source": source,
                }
            )

        return chunks
    
    def process_pdf(self, file_path: str) -> List[Document]:
        """Extract text from PDF file using PyPDFLoader."""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            return self._split_and_filter(documents, doc_type="pdf", source=file_path)
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")
    
    def process_docx(self, file_path: str) -> List[Document]:
        """Extract text from DOCX file using UnstructuredWordDocumentLoader."""
        try:
            loader = UnstructuredWordDocumentLoader(file_path)
            documents = loader.load()
            return self._split_and_filter(documents, doc_type="docx", source=file_path)
        except Exception as e:
            raise Exception(f"Error processing DOCX: {str(e)}")
    
    def process_txt(self, file_path: str) -> List[Document]:
        """Extract text from TXT file using TextLoader."""
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
            return self._split_and_filter(documents, doc_type="txt", source=file_path)
        except Exception as e:
            raise Exception(f"Error processing TXT: {str(e)}")
    
    def process_html(self, file_path: str) -> List[Document]:
        """Extract text from HTML file using BSHTMLLoader."""
        try:
            loader = BSHTMLLoader(file_path)
            documents = loader.load()
            return self._split_and_filter(documents, doc_type="html", source=file_path)
        except Exception as e:
            raise Exception(f"Error processing HTML: {str(e)}")

    def process_md(self, file_path: str) -> List[Document]:
        """Extract text from Markdown file."""
        try:
            if _MD_LOADER == "unstructured":
                loader = UnstructuredMarkdownLoader(file_path)
                documents = loader.load()
            else:
                loader = TextLoader(file_path, encoding="utf-8")
                documents = loader.load()
            return self._split_and_filter(documents, doc_type="md", source=file_path)
        except Exception as e:
            raise Exception(f"Error processing Markdown: {str(e)}")

    def process_document(self, file_path: str, file_type: str) -> List[Document]:
        """Process document based on file type. Use for unstructured types only (no Excel/CSV/DB)."""
        file_type = file_type.lower()
        if file_type == "pdf":
            return self.process_pdf(file_path)
        if file_type in ["docx", "doc"]:
            return self.process_docx(file_path)
        if file_type == "txt":
            return self.process_txt(file_path)
        if file_type in ["html", "htm"]:
            return self.process_html(file_path)
        if file_type in ["md", "markdown"]:
            return self.process_md(file_path)
        raise ValueError(f"Unsupported file type for unstructured processing: {file_type}")

