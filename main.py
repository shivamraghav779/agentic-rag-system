"""FastAPI application main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import init_db_async
from app.api.v1 import api_router

# Initialize FastAPI app
app = FastAPI(
    title="Private Document Chatbot",
    description="A secure RAG-based chatbot for private documents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Root endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Private Document Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    await init_db_async()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

