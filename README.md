# 📄 Private Document Chatbot (RAG-based AI)

A secure private chatbot that allows users to upload personal documents (PDF, DOCX, TXT, HTML) and interactively chat with their content.

The system processes documents, builds contextual embeddings, and enables accurate, document-grounded conversations—ensuring privacy and relevance.

## ✨ Key Features

- 🔐 **Private & secure document handling** - Your documents stay on your server
- 📂 **Multiple file formats** - Supports PDF, DOCX, TXT, and HTML files
- 💬 **Interactive chat** - Chat directly with uploaded documents
- 🧠 **Context-aware responses** - Uses document retrieval for accurate answers
- 🚀 **CPU-optimized** - Works efficiently on CPU machines without GPU
- 🗄️ **PostgreSQL integration** - Robust database for document metadata
- 🔍 **FAISS vector search** - Fast and efficient similarity search

## 🛠️ Technology Stack

- **Vector Database**: FAISS (CPU-optimized)
- **AI Framework**: Langchain
- **Language Model**: Google Gemini
- **Database**: PostgreSQL
- **Backend**: FastAPI
- **Embeddings**: Google Generative AI Embeddings

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
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

### 4. Set up PostgreSQL

Create a PostgreSQL database:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE chatbot_db;

# Exit
\q
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/chatbot_db

# Gemini API Configuration
GOOGLE_API_KEY=your_gemini_api_key_here

# Application Configuration
UPLOAD_DIR=./uploads
VECTOR_STORE_DIR=./vector_stores
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

**Important**: Replace `username`, `password`, and `your_gemini_api_key_here` with your actual values.

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

## 📡 API Endpoints

### 1. Upload Document

**POST** `/upload`

Upload and process a document (PDF, DOCX, TXT, HTML).

```bash
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "document_id": 1,
  "filename": "document.pdf",
  "message": "Document uploaded and processed successfully",
  "chunk_count": 15
}
```

### 2. Chat with Document

**POST** `/chat`

Ask questions about a specific document.

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "question": "What is the main topic of this document?"
  }'
```

**Response:**
```json
{
  "answer": "The main topic is...",
  "source_documents": [
    {
      "content": "Relevant text chunk...",
      "metadata": {
        "source": "path/to/file",
        "chunk_id": 0,
        "type": "pdf"
      }
    }
  ]
}
```

### 3. List Documents

**GET** `/documents`

Get a list of all uploaded documents.

```bash
curl -X GET "http://localhost:8000/documents"
```

### 4. Get Document Info

**GET** `/documents/{document_id}`

Get information about a specific document.

```bash
curl -X GET "http://localhost:8000/documents/1"
```

### 5. Delete Document

**DELETE** `/documents/{document_id}`

Delete a document and its associated data.

```bash
curl -X DELETE "http://localhost:8000/documents/1"
```

## 📁 Project Structure

```
chatbot/
├── main.py                 # FastAPI application and endpoints
├── config.py              # Configuration settings
├── database.py            # Database models and session management
├── document_processor.py  # Document parsing and chunking
├── vector_store.py        # FAISS vector store management
├── rag_chain.py          # RAG chain implementation
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (create this)
├── .gitignore           # Git ignore file
├── uploads/             # Uploaded documents (auto-created)
└── vector_stores/       # FAISS vector stores (auto-created)
```

## 🔧 Configuration

### Chunking Parameters

Adjust document chunking in `.env`:

- `CHUNK_SIZE`: Size of each text chunk (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200)

### File Storage

- `UPLOAD_DIR`: Directory for uploaded files (default: `./uploads`)
- `VECTOR_STORE_DIR`: Directory for FAISS indexes (default: `./vector_stores`)

## 🔒 Security Considerations

1. **API Key Security**: Never commit your `.env` file with API keys
2. **File Access**: Ensure proper file permissions on upload directories
3. **Database Security**: Use strong PostgreSQL credentials
4. **Network Security**: Consider adding authentication for production use

## 🐛 Troubleshooting

### Common Issues

1. **Import errors**: Make sure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Database connection error**: Verify PostgreSQL is running and credentials are correct

3. **Gemini API error**: Check that your API key is valid and has proper permissions

4. **FAISS errors**: Ensure `faiss-cpu` is installed (not `faiss` which requires GPU)

## 📝 Example Usage

### Python Example

```python
import requests

# Upload a document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload',
        files={'file': f}
    )
    doc_data = response.json()
    document_id = doc_data['document_id']

# Chat with the document
chat_response = requests.post(
    'http://localhost:8000/chat',
    json={
        'document_id': document_id,
        'question': 'What are the key points?'
    }
)
answer = chat_response.json()['answer']
print(answer)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

- Langchain for the AI framework
- FAISS for efficient vector search
- Google Gemini for language models
- FastAPI for the web framework

---

**Note**: This is a CPU-optimized implementation. For GPU acceleration, you can modify the FAISS installation to use `faiss-gpu` instead of `faiss-cpu`.
