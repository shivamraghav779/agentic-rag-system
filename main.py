"""FastAPI application main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db_async
from app.db.base import async_engine
from app.api.v1 import api_router
from app.middleware.exception_handling import ExceptionHandlingMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.middleware.response_headers import ResponseHeadersMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="Private Document Chatbot",
    description="A secure RAG-based chatbot for private documents",
    version="1.0.0"
)

# Structured logging (JSON) + request correlation + error handling
configure_logging()
app.add_middleware(ExceptionHandlingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ResponseHeadersMiddleware)

# CORS middleware
allowed_origins = [o.strip() for o in str(settings.allowed_origins).split(",") if o.strip()]
if allowed_origins == ["*"]:
    allowed_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
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
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "detail": str(e)},
        )


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

