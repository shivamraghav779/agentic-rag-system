"""Statistics and dashboard schemas."""
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime


class UserStatistics(BaseModel):
    """User-level statistics."""
    total_documents: int = 0
    total_conversations: int = 0
    total_chats: int = 0
    total_tokens_used: int = 0
    chats_today: int = 0
    chats_remaining_today: int = 0
    chat_limit: int = 0
    documents_by_category: Dict[str, int] = {}
    recent_activity: List[Dict] = []


class OrganizationStatistics(BaseModel):
    """Organization-level statistics."""
    organization_id: int
    organization_name: str
    total_users: int = 0
    total_documents: int = 0
    total_conversations: int = 0
    total_chats: int = 0
    total_tokens_used: int = 0
    active_users: int = 0
    documents_by_category: Dict[str, int] = {}
    users_by_role: Dict[str, int] = {}
    recent_activity: List[Dict] = []


class AdminStatistics(BaseModel):
    """Admin-level statistics (system-wide)."""
    total_organizations: int = 0
    total_users: int = 0
    total_documents: int = 0
    total_conversations: int = 0
    total_chats: int = 0
    total_tokens_used: int = 0
    active_organizations: int = 0
    active_users: int = 0
    users_by_role: Dict[str, int] = {}
    documents_by_category: Dict[str, int] = {}
    organizations_stats: List[OrganizationStatistics] = []
    recent_activity: List[Dict] = []


class ActivityItem(BaseModel):
    """Activity item for recent activity."""
    type: str  # 'document_upload', 'chat', 'conversation', 'user_created'
    description: str
    timestamp: datetime
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    document_id: Optional[int] = None
    document_name: Optional[str] = None

