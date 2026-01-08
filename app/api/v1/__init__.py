"""API v1 routes."""
from fastapi import APIRouter
from app.api.v1 import auth, documents, chat, admin, organizations, users, statistics, categories

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])
api_router.include_router(categories.router, prefix="", tags=["categories"])

