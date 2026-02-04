# Project Architecture Documentation

## Overview

This document describes the architecture of the AI Business Knowledge System - a secure, multi-tenant chatbot application that allows users to upload documents and interactively chat with their content using RAG (Retrieval-Augmented Generation).

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│                    (API Consumers)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP/REST API
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      API Layer                               │
│              (FastAPI Routes - app/api/v1/)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Auth    │ │ Documents│ │   Chat   │ │   Users  │      │
│  │  Routes  │ │  Routes  │ │  Routes  │ │  Routes  │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
└───────┼────────────┼────────────┼────────────┼────────────┘
        │            │            │            │
        │            │            │            │
┌───────▼────────────▼────────────▼────────────▼────────────┐
│                   Service Layer                             │
│            (Business Logic - app/services/)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Auth    │ │ Document │ │   Chat   │ │   User   │      │
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
│       │            │            │            │             │
│  ┌────▼────────────▼────────────▼────────────▼─────┐      │
│  │  Document Processor │ RAG Chain │ Vector Store  │      │
│  └─────────────────────────────────────────────────┘      │
└───────┬────────────────────────────────────────────────────┘
        │
        │
┌───────▼────────────────────────────────────────────────────┐
│                    CRUD Layer                               │
│          (Data Access - app/crud/)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │   User   │ │ Document │ │Conversatn│ │  Chat    │      │
│  │   CRUD   │ │   CRUD   │ │   CRUD   │ │  CRUD    │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
└───────┼─────────────┼─────────────┼────────────┼────────────┘
        │             │             │            │
        └─────────────┴─────────────┴────────────┘
                            │
                            │ SQLAlchemy ORM
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  Database Layer                              │
│                    MySQL Database                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Users   │ │Documents │ │Conversatn│ │ChatHist. │      │
│  │  Tables  │ │  Tables  │ │  Tables  │ │  Tables  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              External Services                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Gemini AI │  │  FAISS Vector│  │  File System │    │
│  │   (Google)  │  │    Store     │  │   (Uploads)  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Layered Architecture

The application follows a **3-layer architecture**:

### 1. API Layer (Routes)
**Location**: `app/api/v1/`

**Responsibility**:
- Handle HTTP requests and responses
- Validate input using Pydantic schemas
- Authenticate and authorize requests
- Delegate business logic to service layer

**Components**:
- `auth.py`: Authentication endpoints (signup, login, refresh token)
- `users.py`: User management endpoints
- `documents.py`: Document upload and management
- `chat.py`: Chat and conversation endpoints
- `organizations.py`: Organization management
- `admin.py`: Admin-specific operations
- `statistics.py`: Statistics and dashboard endpoints

**Example**:
```python
@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    document_service = DocumentService(db)
    return await document_service.upload_document(
        file=file,
        user=current_user,
        organization_id=organization_id,
        category=category
    )
```

### 2. Service Layer (Business Logic)
**Location**: `app/services/`

**Responsibility**:
- Implement business logic and rules
- Coordinate between multiple CRUD operations
- Handle complex workflows
- Integrate with external services (AI, Vector Store)

**Components**:
- `auth_service.py`: Authentication business logic
- `user_service.py`: User management logic
- `document_service.py`: Document processing and management
- `chat_service.py`: Chat and conversation logic
- `organization_service.py`: Organization management
- `statistics_service.py`: Statistics and dashboard data generation
- `document_processor.py`: Document parsing and chunking
- `rag_chain.py`: RAG implementation with Gemini
- `vector_store.py`: FAISS vector store management

**Example**:
```python
class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.document_crud = document_crud
        self.document_processor = DocumentProcessor()
        self.vector_store_manager = VectorStoreManager()
    
    def upload_document(self, file, user, organization_id, category):
        # Business logic: validate, process, store
        # Coordinate: CRUD operations, file processing, vector store
        pass
```

### 3. CRUD Layer (Data Access)
**Location**: `app/crud/`

**Responsibility**:
- Abstract database operations
- Provide reusable data access methods
- Handle database queries and transactions

**Components**:
- `base.py`: Generic CRUD base class
- `user.py`: User CRUD operations
- `document.py`: Document CRUD operations
- `organization.py`: Organization CRUD operations
- `conversation.py`: Conversation CRUD operations
- `chat_history.py`: ChatHistory CRUD operations

**Example**:
```python
class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
```

## Directory Structure

```
chatbot/
├── app/
│   ├── api/                    # API routes
│   │   ├── deps.py            # Dependencies (auth, DB session)
│   │   └── v1/                # API version 1
│   │       ├── auth.py        # Authentication endpoints
│   │       ├── users.py       # User management
│   │       ├── documents.py   # Document management
│   │       ├── chat.py        # Chat endpoints
│   │       ├── organizations.py  # Organization management
│   │       ├── admin.py       # Admin operations
│   │       └── statistics.py  # Statistics and dashboard
│   │
│   ├── core/                  # Core configuration
│   │   ├── config.py          # Settings and configuration
│   │   └── security.py        # Security utilities (JWT, password hashing)
│   │
│   ├── crud/                   # Data access layer
│   │   ├── base.py            # Base CRUD class
│   │   ├── user.py            # User CRUD
│   │   ├── document.py        # Document CRUD
│   │   ├── organization.py    # Organization CRUD
│   │   ├── conversation.py    # Conversation CRUD
│   │   └── chat_history.py   # ChatHistory CRUD
│   │
│   ├── db/                     # Database configuration
│   │   ├── base.py            # SQLAlchemy base
│   │   └── session.py         # Database session management
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py            # User model
│   │   ├── document.py        # Document model
│   │   ├── organization.py    # Organization model
│   │   ├── conversation.py    # Conversation model
│   │   └── chat_history.py    # ChatHistory model
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py            # User schemas
│   │   ├── document.py        # Document schemas
│   │   ├── organization.py    # Organization schemas
│   │   ├── chat.py            # Chat schemas
│   │   └── statistics.py      # Statistics schemas
│   │
│   └── services/               # Business logic layer
│       ├── auth_service.py     # Authentication service
│       ├── user_service.py     # User management service
│       ├── document_service.py # Document service
│       ├── chat_service.py    # Chat service
│       ├── organization_service.py  # Organization service
│       ├── statistics_service.py    # Statistics service
│       ├── document_processor.py    # Document processing
│       ├── rag_chain.py       # RAG implementation
│       └── vector_store.py    # Vector store management
│
├── alembic/                    # Database migrations
│   ├── versions/              # Migration scripts
│   └── env.py                 # Alembic environment
│
├── scripts/                     # Utility scripts
│   ├── create_admin.py        # Create admin user
│   └── create_database.py     # Database setup
│
├── uploads/                     # Uploaded documents
├── vector_stores/              # FAISS vector stores
├── main.py                      # Application entry point
├── requirements.txt            # Python dependencies
└── alembic.ini                 # Alembic configuration
```

### Artifacts (per-organization storage)

Vector stores, structured data (SQLite), and uploads are stored **per organization** under `artifacts/{organization_id}/`:

- `artifacts/{org_id}/uploads/` — raw uploaded files
- `artifacts/{org_id}/vector_store/` — FAISS indexes (one folder per document)
- `artifacts/{org_id}/structured_data/` — SQLite DBs from Excel/CSV/DB uploads

See **ARTIFACTS_AND_PIPELINE.md** for the full layout, upload/chat pipeline, and robustness suggestions.

## Data Flow

### Document Upload Flow

```
1. Client → POST /api/v1/documents/upload
   ↓
2. API Route (documents.py)
   - Validates file
   - Authenticates user
   - Checks organization access
   ↓
3. DocumentService.upload_document()
   - Validates user can upload
   - Saves file to disk
   - Processes document (DocumentProcessor)
   - Creates vector store (VectorStoreManager)
   - Saves metadata (Document CRUD)
   ↓
4. DocumentProcessor.process_document()
   - Loads document (PDF/DOCX/TXT/HTML)
   - Splits into chunks
   - Returns Document objects
   ↓
5. VectorStoreManager.create_vector_store()
   - Generates embeddings (Gemini)
   - Creates FAISS index
   - Saves to disk
   ↓
6. Document CRUD.create_from_dict()
   - Saves to database
   ↓
7. Response → Client
```

### Chat Flow

```
1. Client → POST /api/v1/chat
   ↓
2. API Route (chat.py)
   - Validates request
   - Authenticates user
   ↓
3. ChatService.chat_with_document()
   - Checks rate limit
   - Validates document access
   - Gets/creates conversation
   - Retrieves conversation history
   ↓
4. RAGChain.query()
   - Loads vector store
   - Performs similarity search
   - Retrieves relevant chunks
   - Constructs prompt with:
     - System prompt (user's custom)
     - Instruction prompt (default)
     - Conversation history (last 5 chats)
     - Current date/time
     - Retrieved document chunks
     - User's question
   ↓
5. Gemini API
   - Generates response
   - Returns answer + token counts
   ↓
6. ChatService
   - Saves chat history (ChatHistory CRUD)
   - Updates user token usage
   - Updates conversation timestamp
   ↓
7. Response → Client
```

## Key Technologies

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.8+**: Programming language

### Database
- **MySQL**: Relational database
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migration tool

### AI/ML
- **Google Gemini**: LLM for generating responses and embeddings
- **FAISS**: Vector similarity search library
- **Langchain**: Document loaders and text splitting

### Authentication & Security
- **JWT**: JSON Web Tokens for authentication
- **Argon2**: Password hashing algorithm
- **Pydantic**: Data validation

### Document Processing
- **PyPDFLoader**: PDF parsing
- **UnstructuredWordDocumentLoader**: DOCX parsing
- **TextLoader**: TXT parsing
- **BSHTMLLoader**: HTML parsing

## Design Patterns

### 1. Repository Pattern
The CRUD layer implements the Repository pattern, abstracting database operations:
```python
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(self.model).filter(self.model.email == email).first()
```

### 2. Service Layer Pattern
Business logic is encapsulated in service classes:
```python
class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.document_crud = document_crud
        # ... other dependencies
```

### 3. Dependency Injection
FastAPI's dependency injection is used throughout:
```python
async def upload_document(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
```

### 4. Factory Pattern
Service instances are created per request:
```python
document_service = DocumentService(db)
```

### 5. Custom Type Decorator Pattern
Custom SQLAlchemy types for handling enum value mapping:
```python
class UserRoleType(TypeDecorator):
    """Custom type to map database enum values to Python UserRole enum."""
    # Handles case mismatches and legacy values without database migration
```

## Multi-Tenancy

The system implements hierarchical multi-tenancy:

```
SuperAdmin
  └── Admin
      └── Organization
          ├── OrgAdmin
          └── OrgUser
```

**Key Features**:
- Role-based access control (RBAC)
- Organization-scoped resources (documents, chats)
- Private users (USER role) separate from organization users
- Access control enforced at service layer

See `MULTI_TENANCY.md` for detailed documentation.

## Security Features

1. **Authentication**: JWT-based with refresh tokens
2. **Password Hashing**: Argon2 algorithm
3. **Authorization**: Role-based access control
4. **Input Validation**: Pydantic schemas
5. **SQL Injection Protection**: Parameterized queries via SQLAlchemy
6. **Rate Limiting**: Per-user chat limits
7. **Organization Isolation**: Documents and chats scoped to organizations

## Error Handling

- **Custom Exceptions**: Domain-specific exceptions
- **HTTP Exceptions**: Standard HTTP status codes
- **Validation Errors**: Pydantic validation with detailed messages
- **Global Exception Handlers**: Consistent error responses

## Database Migrations

- **Alembic**: Manages schema changes
- **Version Control**: All migrations are versioned
- **Rollback Support**: Can rollback to previous versions

## Testing Strategy

(To be implemented)
- Unit tests for services
- Integration tests for API endpoints
- Mock external services (Gemini API)

## Deployment

### Requirements
- Python 3.8+
- MySQL 5.7+
- Sufficient disk space for uploads and vector stores

### Environment Variables
See `.env` file for configuration:
- Database connection
- Gemini API key
- JWT secrets
- File paths
- Application settings

## Performance Considerations

1. **Vector Store**: FAISS for efficient similarity search
2. **Database Indexing**: Indexed columns for fast queries
3. **Connection Pooling**: SQLAlchemy connection pooling
4. **Async Operations**: FastAPI async endpoints
5. **Caching**: (To be implemented) Redis for frequently accessed data

## Scalability

1. **Horizontal Scaling**: Stateless API servers
2. **Database Scaling**: Read replicas for read-heavy operations
3. **Vector Store**: Can be moved to distributed storage
4. **File Storage**: Can be moved to object storage (S3, etc.)

## Future Enhancements

1. **Caching Layer**: Redis for frequently accessed data
2. **Background Jobs**: Celery for async document processing
3. **Monitoring**: Application performance monitoring
4. **Analytics**: Usage analytics and reporting
5. **Document Versioning**: Track document changes over time
6. **Bulk Operations**: Bulk document upload/management
7. **Advanced RAG**: Multi-document queries, citation tracking

## Development Guidelines

1. **Follow Layered Architecture**: Routes → Services → CRUD
2. **Use Type Hints**: All functions should have type hints
3. **Document Code**: Docstrings for all classes and methods
4. **Error Handling**: Use appropriate exceptions
5. **Testing**: Write tests for new features
6. **Migrations**: Always create migrations for schema changes

## API Documentation

- **Swagger UI**: Available at `/docs` (when running)
- **ReDoc**: Available at `/redoc` (when running)
- **Markdown Docs**: See `API_DOCUMENTATION.md`

## Contributing

1. Follow the layered architecture
2. Write services for business logic
3. Use CRUD layer for data access
4. Add proper error handling
5. Write tests
6. Update documentation

