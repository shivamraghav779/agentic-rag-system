"""Document processing module for various file types using Langchain loaders."""
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    TextLoader,
    BSHTMLLoader,
)
from app.core.config import settings


class DocumentProcessor:
    """Processes various document types using Langchain loaders and splits them into chunks."""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
        )
    
    def process_pdf(self, file_path: str) -> List[Document]:
        """Extract text from PDF file using PyPDFLoader."""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            # Split into chunks and add metadata
            chunks = self.text_splitter.split_documents(documents)
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_id": i,
                    "type": "pdf",
                    "source": file_path
                })
            
            return chunks
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")
    
    def process_docx(self, file_path: str) -> List[Document]:
        """Extract text from DOCX file using UnstructuredWordDocumentLoader."""
        try:
            loader = UnstructuredWordDocumentLoader(file_path)
            documents = loader.load()
            
            # Split into chunks and add metadata
            chunks = self.text_splitter.split_documents(documents)
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_id": i,
                    "type": "docx",
                    "source": file_path
                })
            
            return chunks
        except Exception as e:
            raise Exception(f"Error processing DOCX: {str(e)}")
    
    def process_txt(self, file_path: str) -> List[Document]:
        """Extract text from TXT file using TextLoader."""
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
            
            # Split into chunks and add metadata
            chunks = self.text_splitter.split_documents(documents)
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_id": i,
                    "type": "txt",
                    "source": file_path
                })
            
            return chunks
        except Exception as e:
            raise Exception(f"Error processing TXT: {str(e)}")
    
    def process_html(self, file_path: str) -> List[Document]:
        """Extract text from HTML file using BSHTMLLoader."""
        try:
            loader = BSHTMLLoader(file_path)
            documents = loader.load()
            
            # Split into chunks and add metadata
            chunks = self.text_splitter.split_documents(documents)
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_id": i,
                    "type": "html",
                    "source": file_path
                })
            
            return chunks
        except Exception as e:
            raise Exception(f"Error processing HTML: {str(e)}")
    
    def process_document(self, file_path: str, file_type: str) -> List[Document]:
        """Process document based on file type using appropriate Langchain loader."""
        file_type = file_type.lower()
        
        if file_type == 'pdf':
            return self.process_pdf(file_path)
        elif file_type in ['docx', 'doc']:
            return self.process_docx(file_path)
        elif file_type == 'txt':
            return self.process_txt(file_path)
        elif file_type in ['html', 'htm']:
            return self.process_html(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

