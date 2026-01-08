# 📄 AI Business Knowledge System

A secure, multi-tenant RAG-based chatbot application that allows organizations and users to upload documents (PDF, DOCX, TXT, HTML) and interactively chat with their content using AI-powered retrieval-augmented generation.

The system processes documents, builds contextual embeddings, and enables accurate, document-grounded conversations—ensuring privacy, security, and relevance for enterprise knowledge management.

## ✨ Key Features

- 🔐 **Multi-Tenant Architecture** - Hierarchical organization structure with role-based access control
- 📂 **Multiple File Formats** - Supports PDF, DOCX, TXT, and HTML files
- 💬 **Interactive Chat** - Chat directly with uploaded documents using RAG
- 🧠 **Context-Aware Responses** - Uses document retrieval for accurate, source-backed answers
- 🚀 **CPU-Optimized** - Works efficiently on CPU machines without GPU
- 🗄️ **MySQL Integration** - Robust database for metadata, users, and conversations
- 🔍 **FAISS Vector Search** - Fast and efficient similarity search
- 📊 **Dashboard & Analytics** - Comprehensive statistics for users, organizations, and admins
- 🔑 **JWT Authentication** - Secure authentication with refresh tokens
- 👥 **Role-Based Access Control** - SuperAdmin, Admin, OrgAdmin, OrgUser, and Private User roles

## 🛠️ Technology Stack

- **Vector Database**: FAISS (CPU-optimized)
- **AI Framework**: Langchain (for document loaders and vector store)
- **Language Model**: Google Gemini (for responses and embeddings)
- **Database**: MySQL 5.7+
- **Backend**: FastAPI
- **Authentication**: JWT with Argon2 password hashing
- **Architecture**: Layered architecture (Routes → Services → CRUD → Database)

## 📋 Prerequisites

- Python 3.8 or higher
- MySQL 5.7 or higher (or MariaDB 10.3+)
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd chatbot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up MySQL Database

You can use the provided scripts to create the database:

**Option 1: Using Python script (Recommended)**
```bash
python scripts/create_database.py
```

**Option 2: Using SQL script**
```bash
mysql -u root -p < scripts/create_database.sql
```

**Option 3: Manual setup**
```bash
mysql -u root -p

CREATE DATABASE chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'chatbot_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON chatbot.* TO 'chatbot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/chatbot

# Gemini API Configuration
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-pro
EMBEDDING_MODEL=models/embedding-001

# JWT Configuration
SECRET_KEY=your_secret_key_here  # Generate using: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Configuration
UPLOAD_DIR=./uploads
VECTOR_STORE_DIR=./vector_stores
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# LLM Configuration
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=2048
RETRIEVAL_K=5
SOURCE_DOC_PREVIEW_LENGTH=200
DEFAULT_INSTRUCTION_PROMPT=You are a helpful assistant that answers questions based on the provided documents.

# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# File Upload
MAX_FILE_SIZE=10485760  # 10MB in bytes

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

**Important**: 
- Replace `username`, `password`, and `your_gemini_api_key_here` with your actual values
- Generate a secure `SECRET_KEY` using: `openssl rand -hex 32`

### 6. Run database migrations

```bash
# Initialize Alembic (if not already done)
alembic upgrade head
```

### 7. Create an admin user

```bash
python scripts/create_admin.py
```

This will create a SuperAdmin user for initial system access.

## 🏃 Running the Application

### Start the server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, you can access:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc
- **API Root**: http://localhost:8000/api/v1

## 📡 API Endpoints Overview

### Authentication (`/api/v1/auth`)
- `POST /signup` - Register a new private user
- `POST /login` - Login and get access token
- `GET /me` - Get current user information
- `POST /refresh` - Refresh access token
- `PATCH /me/system-prompt` - Update user's system prompt

### Documents (`/api/v1/documents`)
- `POST /upload` - Upload and process a document
- `GET /` - List documents (organization-scoped)
- `GET /{document_id}` - Get document information
- `DELETE /{document_id}` - Delete a document

### Chat (`/api/v1/chat`)
- `POST /` - Chat with a document
- `GET /history` - Get chat history
- `GET /history/{chat_id}` - Get specific chat entry
- `POST /conversations` - Create a conversation
- `GET /conversations` - List conversations
- `GET /conversations/{conversation_id}` - Get conversation
- `PATCH /conversations/{conversation_id}` - Update conversation
- `DELETE /conversations/{conversation_id}` - Delete conversation

### Users (`/api/v1/users`)
- `POST /` - Create user (Admin only)
- `GET /` - List users (role-based filtering)
- `GET /{user_id}` - Get user information
- `PATCH /{user_id}` - Update user (Admin only)
- `DELETE /{user_id}` - Delete user (SuperAdmin only)
- `PATCH /{user_id}/password` - Update password
- `PATCH /{user_id}/chat-limit` - Update chat limit
- `PATCH /{user_id}/activate` - Toggle active status

### Organizations (`/api/v1/organizations`)
- `POST /` - Create organization (Admin only)
- `GET /` - List organizations (role-based)
- `GET /{organization_id}` - Get organization
- `PATCH /{organization_id}` - Update organization
- `DELETE /{organization_id}` - Delete organization (SuperAdmin only)
- `GET /{organization_id}/users` - List organization users
- `POST /{organization_id}/users` - Create organization user

### Statistics (`/api/v1/statistics`)
- `GET /user` - Get user statistics
- `GET /organization/{organization_id}` - Get organization statistics
- `GET /admin` - Get admin/system statistics

### Admin (`/api/v1/admin`)
- `GET /superadmins` - List SuperAdmins
- `POST /superadmins` - Create SuperAdmin
- `GET /admins` - List Admins
- `POST /admins` - Create Admin

For detailed API documentation, see:
- **Complete API Docs**: `CRUD_API_DOCUMENTATION.md`
- **Frontend Guide**: `FRONTEND_IMPLEMENTATION_GUIDE.md`

## 📁 Project Structure

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
│   │   ├── conversation.py   # Conversation CRUD
│   │   └── chat_history.py    # ChatHistory CRUD
│   │
│   ├── db/                     # Database configuration
│   │   ├── base.py            # SQLAlchemy base
│   │   └── session.py         # Database session management
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py            # User model
│   │   ├── document.py        # Document model
│   │   ├── organization.py    # Organization model
│   │   ├── conversation.py   # Conversation model
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
│   ├── create_database.py     # Database setup
│   └── create_user_with_org.py  # Create user with organization
│
├── uploads/                     # Uploaded documents (auto-created)
├── vector_stores/              # FAISS vector stores (auto-created)
├── main.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
├── .env                        # Environment variables (create this)
│
└── Documentation/
    ├── README.md                      # This file
    ├── CRUD_API_DOCUMENTATION.md      # Complete API documentation
    ├── FRONTEND_IMPLEMENTATION_GUIDE.md # Frontend developer guide
    ├── PROJECT_ARCHITECTURE.md        # System architecture
    ├── MULTI_TENANCY.md               # Multi-tenancy guide
    └── MIGRATIONS.md                  # Database migration guide
```

## 🏗️ Architecture

The application follows a **layered architecture**:

```
Routes (API Endpoints) 
    ↓
Service Layer (Business Logic)
    ↓
CRUD Layer (Data Access)
    ↓
Database Models
```

This ensures:
- **Separation of Concerns**: Each layer has a specific responsibility
- **Maintainability**: Business logic is centralized in services
- **Testability**: Services can be tested independently
- **Scalability**: Easy to add new features

For detailed architecture documentation, see `PROJECT_ARCHITECTURE.md`.

## 👥 User Roles & Multi-Tenancy

The system supports hierarchical multi-tenancy:

```
SuperAdmin
  └── Admin
      └── Organization
          ├── OrgAdmin
          └── OrgUser
```

**Roles**:
- **SuperAdmin**: Full system access
- **Admin**: Can manage organizations
- **OrgAdmin**: Manages organization and users
- **OrgUser**: Regular organization user
- **User**: Private user (not in organization)

For detailed multi-tenancy documentation, see `MULTI_TENANCY.md`.

## 📝 Example Usage

### 1. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "secure_password"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### 3. Upload a Document (Organization User)

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload?category=HR" \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@document.pdf"
```

### 4. Chat with Document

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "question": "What is the main topic of this document?"
  }'
```

### 5. Get User Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/statistics/user" \
  -H "Authorization: Bearer <access_token>"
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

- **Database**: `DATABASE_URL` - MySQL connection string
- **Gemini API**: `GOOGLE_API_KEY` - Your Gemini API key
- **JWT**: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- **File Upload**: `MAX_FILE_SIZE` - Maximum file size in bytes
- **Chunking**: `CHUNK_SIZE`, `CHUNK_OVERLAP` - Document chunking parameters
- **LLM**: `TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `RETRIEVAL_K` - Model parameters

### Database Migrations

The project uses Alembic for database migrations:

```bash
# Create a new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🔒 Security Features

1. **JWT Authentication**: Secure token-based authentication
2. **Password Hashing**: Argon2 algorithm for password security
3. **Role-Based Access Control**: Hierarchical permission system
4. **Organization Isolation**: Documents and chats scoped to organizations
5. **Rate Limiting**: Per-user chat limits
6. **Input Validation**: Pydantic schemas for all inputs
7. **SQL Injection Protection**: Parameterized queries via SQLAlchemy

## 🐛 Troubleshooting

### Common Issues

1. **Import errors**: Make sure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Database connection error**: 
   - Verify MySQL is running
   - Check credentials in `.env`
   - Ensure database exists

3. **Gemini API error**: 
   - Verify API key is correct
   - Check API key permissions
   - Ensure you have quota available

4. **FAISS errors**: 
   - Ensure `faiss-cpu` is installed (not `faiss` which requires GPU)
   - Check Python version compatibility

5. **Migration errors**:
   - Ensure database is created
   - Check Alembic version
   - Review migration scripts for conflicts

6. **Enum mapping errors**:
   - The system uses `UserRoleType` custom type decorator
   - Handles database enum values automatically
   - No migration needed for enum value changes

## 📚 Documentation

- **API Documentation**: `CRUD_API_DOCUMENTATION.md` - Complete API reference
- **Frontend Guide**: `FRONTEND_IMPLEMENTATION_GUIDE.md` - Frontend developer guide with wireframes
- **Architecture**: `PROJECT_ARCHITECTURE.md` - System architecture details
- **Multi-Tenancy**: `MULTI_TENANCY.md` - Multi-tenancy implementation guide
- **Migrations**: `MIGRATIONS.md` - Database migration guide

## 🧪 Development

### Running Tests

(To be implemented)

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all functions
- Document all classes and methods with docstrings

### Adding New Features

1. Create/update models in `app/models/`
2. Create CRUD operations in `app/crud/`
3. Create service in `app/services/`
4. Create API routes in `app/api/v1/`
5. Create schemas in `app/schemas/`
6. Update documentation

## 🤝 Contributing

Contributions are welcome! Please follow the layered architecture pattern:
- Routes → Services → CRUD → Database

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

- Langchain for document loaders and text splitting
- FAISS for efficient vector search
- Google Gemini for language models and embeddings
- FastAPI for the web framework
- SQLAlchemy for ORM
- Alembic for database migrations

---

**Note**: This is a CPU-optimized implementation. For GPU acceleration, you can modify the FAISS installation to use `faiss-gpu` instead of `faiss-cpu`.
