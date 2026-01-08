"""Statistics service layer for dashboard data."""
from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.crud.user import user as user_crud
from app.crud.document import document as document_crud
from app.crud.organization import organization as organization_crud
from app.crud.conversation import conversation as conversation_crud
from app.crud.chat_history import chat_history as chat_history_crud
from app.models.user import User, UserRole
from app.models.document import Document, DocumentCategory
from app.models.organization import Organization
from app.models.conversation import Conversation
from app.models.chat_history import ChatHistory
from app.schemas.statistics import (
    UserStatistics,
    OrganizationStatistics,
    AdminStatistics,
    ActivityItem
)


class StatisticsService:
    """Service for generating statistics and dashboard data."""
    
    def __init__(self, db: Session):
        """Initialize statistics service with database session."""
        self.db = db
    
    def get_user_statistics(self, user: User) -> UserStatistics:
        """
        Get statistics for a specific user.
        
        Args:
            user: User to get statistics for
            
        Returns:
            UserStatistics object
        """
        # Total documents uploaded by user
        total_documents = self.db.query(func.count(Document.id)).filter(
            Document.user_id == user.id
        ).scalar() or 0
        
        # Total conversations
        total_conversations = self.db.query(func.count(Conversation.id)).filter(
            Conversation.user_id == user.id
        ).scalar() or 0
        
        # Total chats
        total_chats = self.db.query(func.count(ChatHistory.id)).filter(
            ChatHistory.user_id == user.id
        ).scalar() or 0
        
        # Total tokens used
        total_tokens = user.used_tokens or 0
        
        # Chats today
        today = datetime.utcnow().date()
        chats_today = self.db.query(func.count(ChatHistory.id)).filter(
            and_(
                ChatHistory.user_id == user.id,
                ChatHistory.created_at >= datetime.combine(today, datetime.min.time())
            )
        ).scalar() or 0
        
        # Chats remaining today
        chats_remaining = max(0, user.chat_limit - chats_today)
        
        # Documents by category
        documents_by_category = {}
        if user.is_organization_user() and user.organization_id:
            category_counts = self.db.query(
                Document.category,
                func.count(Document.id)
            ).filter(
                Document.organization_id == user.organization_id
            ).group_by(Document.category).all()
            
            for category, count in category_counts:
                if category:
                    documents_by_category[category.value] = count
        
        # Recent activity (last 10 activities)
        recent_activity = self._get_user_recent_activity(user.id, limit=10)
        
        return UserStatistics(
            total_documents=total_documents,
            total_conversations=total_conversations,
            total_chats=total_chats,
            total_tokens_used=total_tokens,
            chats_today=chats_today,
            chats_remaining_today=chats_remaining,
            chat_limit=user.chat_limit,
            documents_by_category=documents_by_category,
            recent_activity=recent_activity
        )
    
    def get_organization_statistics(self, organization_id: int, user: User) -> OrganizationStatistics:
        """
        Get statistics for an organization.
        
        Args:
            organization_id: Organization ID
            user: Current user (for access control)
            
        Returns:
            OrganizationStatistics object
        """
        # Verify access
        if not user.can_access_organization(organization_id):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
        
        # Get organization
        organization = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not organization:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Total users in organization
        total_users = self.db.query(func.count(User.id)).filter(
            User.organization_id == organization_id,
            User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
        ).scalar() or 0
        
        # Active users
        active_users = self.db.query(func.count(User.id)).filter(
            User.organization_id == organization_id,
            User.is_active == True,
            User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
        ).scalar() or 0
        
        # Total documents
        total_documents = self.db.query(func.count(Document.id)).filter(
            Document.organization_id == organization_id
        ).scalar() or 0
        
        # Total conversations
        total_conversations = self.db.query(func.count(Conversation.id)).filter(
            Conversation.document_id.in_(
                self.db.query(Document.id).filter(
                    Document.organization_id == organization_id
                )
            )
        ).scalar() or 0
        
        # Total chats
        total_chats = self.db.query(func.count(ChatHistory.id)).filter(
            ChatHistory.document_id.in_(
                self.db.query(Document.id).filter(
                    Document.organization_id == organization_id
                )
            )
        ).scalar() or 0
        
        # Total tokens used by organization users
        total_tokens = self.db.query(func.sum(User.used_tokens)).filter(
            User.organization_id == organization_id
        ).scalar() or 0
        
        # Documents by category
        documents_by_category = {}
        category_counts = self.db.query(
            Document.category,
            func.count(Document.id)
        ).filter(
            Document.organization_id == organization_id
        ).group_by(Document.category).all()
        
        for category, count in category_counts:
            if category:
                documents_by_category[category.value] = count
        
        # Users by role
        users_by_role = {}
        role_counts = self.db.query(
            User.role,
            func.count(User.id)
        ).filter(
            User.organization_id == organization_id
        ).group_by(User.role).all()
        
        for role, count in role_counts:
            if role:
                users_by_role[role.value] = count
        
        # Recent activity
        recent_activity = self._get_organization_recent_activity(organization_id, limit=10)
        
        return OrganizationStatistics(
            organization_id=organization.id,
            organization_name=organization.name,
            total_users=total_users,
            total_documents=total_documents,
            total_conversations=total_conversations,
            total_chats=total_chats,
            total_tokens_used=total_tokens,
            active_users=active_users,
            documents_by_category=documents_by_category,
            users_by_role=users_by_role,
            recent_activity=recent_activity
        )
    
    def get_admin_statistics(self, user: User) -> AdminStatistics:
        """
        Get system-wide statistics for admin users.
        
        Args:
            user: Current user (must be Admin or SuperAdmin)
            
        Returns:
            AdminStatistics object
        """
        # Verify admin access
        if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Total organizations
        total_organizations = self.db.query(func.count(Organization.id)).scalar() or 0
        
        # Active organizations
        active_organizations = self.db.query(func.count(Organization.id)).filter(
            Organization.is_active == True
        ).scalar() or 0
        
        # Total users
        total_users = self.db.query(func.count(User.id)).scalar() or 0
        
        # Active users
        active_users = self.db.query(func.count(User.id)).filter(
            User.is_active == True
        ).scalar() or 0
        
        # Total documents
        total_documents = self.db.query(func.count(Document.id)).scalar() or 0
        
        # Total conversations
        total_conversations = self.db.query(func.count(Conversation.id)).scalar() or 0
        
        # Total chats
        total_chats = self.db.query(func.count(ChatHistory.id)).scalar() or 0
        
        # Total tokens used
        total_tokens = self.db.query(func.sum(User.used_tokens)).scalar() or 0
        
        # Users by role
        users_by_role = {}
        role_counts = self.db.query(
            User.role,
            func.count(User.id)
        ).group_by(User.role).all()
        
        for role, count in role_counts:
            if role:
                users_by_role[role.value] = count
        
        # Documents by category
        documents_by_category = {}
        category_counts = self.db.query(
            Document.category,
            func.count(Document.id)
        ).group_by(Document.category).all()
        
        for category, count in category_counts:
            if category:
                documents_by_category[category.value] = count
        
        # Organization statistics (optimized bulk calculation)
        organizations = self.db.query(Organization).all()
        organizations_stats = []
        
        # Bulk calculate user counts per organization
        user_counts = dict(
            self.db.query(
                User.organization_id,
                func.count(User.id)
            ).filter(
                User.organization_id.isnot(None),
                User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
            ).group_by(User.organization_id).all()
        )
        
        # Bulk calculate active user counts
        active_user_counts = dict(
            self.db.query(
                User.organization_id,
                func.count(User.id)
            ).filter(
                User.organization_id.isnot(None),
                User.is_active == True,
                User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
            ).group_by(User.organization_id).all()
        )
        
        # Bulk calculate document counts
        doc_counts = dict(
            self.db.query(
                Document.organization_id,
                func.count(Document.id)
            ).group_by(Document.organization_id).all()
        )
        
        # Bulk calculate token usage per organization
        token_counts = dict(
            self.db.query(
                User.organization_id,
                func.sum(User.used_tokens)
            ).filter(
                User.organization_id.isnot(None)
            ).group_by(User.organization_id).all()
        )
        
        for org in organizations:
            # Get document IDs for this org for conversation/chat counts
            org_doc_ids = [doc_id for (doc_id,) in self.db.query(Document.id).filter(
                Document.organization_id == org.id
            ).all()]
            
            org_conversations = self.db.query(func.count(Conversation.id)).filter(
                Conversation.document_id.in_(org_doc_ids)
            ).scalar() or 0 if org_doc_ids else 0
            
            org_chats = self.db.query(func.count(ChatHistory.id)).filter(
                ChatHistory.document_id.in_(org_doc_ids)
            ).scalar() or 0 if org_doc_ids else 0
            
            # Documents by category for this org
            org_docs_by_category = {}
            org_category_counts = self.db.query(
                Document.category,
                func.count(Document.id)
            ).filter(
                Document.organization_id == org.id
            ).group_by(Document.category).all()
            
            for category, count in org_category_counts:
                if category:
                    org_docs_by_category[category.value] = count
            
            # Users by role for this org
            org_users_by_role = {}
            org_role_counts = self.db.query(
                User.role,
                func.count(User.id)
            ).filter(
                User.organization_id == org.id
            ).group_by(User.role).all()
            
            for role, count in org_role_counts:
                if role:
                    org_users_by_role[role.value] = count
            
            organizations_stats.append(OrganizationStatistics(
                organization_id=org.id,
                organization_name=org.name,
                total_users=user_counts.get(org.id, 0),
                total_documents=doc_counts.get(org.id, 0),
                total_conversations=org_conversations,
                total_chats=org_chats,
                total_tokens_used=int(token_counts.get(org.id, 0) or 0),
                active_users=active_user_counts.get(org.id, 0),
                documents_by_category=org_docs_by_category,
                users_by_role=org_users_by_role,
                recent_activity=[]  # Omit for performance in admin view
            ))
        
        # Recent activity
        recent_activity = self._get_admin_recent_activity(limit=20)
        
        return AdminStatistics(
            total_organizations=total_organizations,
            total_users=total_users,
            total_documents=total_documents,
            total_conversations=total_conversations,
            total_chats=total_chats,
            total_tokens_used=total_tokens,
            active_organizations=active_organizations,
            active_users=active_users,
            users_by_role=users_by_role,
            documents_by_category=documents_by_category,
            organizations_stats=organizations_stats,
            recent_activity=recent_activity
        )
    
    def _get_user_recent_activity(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent activity for a user."""
        activities = []
        
        # Recent document uploads
        recent_docs = self.db.query(Document).filter(
            Document.user_id == user_id
        ).order_by(Document.upload_date.desc()).limit(limit).all()
        
        for doc in recent_docs:
            activities.append({
                "type": "document_upload",
                "description": f"Uploaded document: {doc.filename}",
                "timestamp": doc.upload_date,
                "document_id": doc.id,
                "document_name": doc.filename
            })
        
        # Recent chats
        recent_chats = self.db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id
        ).order_by(ChatHistory.created_at.desc()).limit(limit).all()
        
        for chat in recent_chats:
            doc = self.db.query(Document).filter(Document.id == chat.document_id).first()
            activities.append({
                "type": "chat",
                "description": f"Chatted with document: {doc.filename if doc else 'Unknown'}",
                "timestamp": chat.created_at,
                "document_id": chat.document_id,
                "document_name": doc.filename if doc else None
            })
        
        # Sort by timestamp and return top N
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
    
    def _get_organization_recent_activity(self, organization_id: int, limit: int = 10) -> List[Dict]:
        """Get recent activity for an organization."""
        activities = []
        
        # Recent document uploads
        recent_docs = self.db.query(Document).filter(
            Document.organization_id == organization_id
        ).order_by(Document.upload_date.desc()).limit(limit).all()
        
        for doc in recent_docs:
            user = self.db.query(User).filter(User.id == doc.user_id).first()
            activities.append({
                "type": "document_upload",
                "description": f"{user.username if user else 'Unknown'} uploaded: {doc.filename}",
                "timestamp": doc.upload_date,
                "user_id": doc.user_id,
                "user_name": user.username if user else None,
                "document_id": doc.id,
                "document_name": doc.filename
            })
        
        # Recent chats
        org_doc_ids = [doc_id for (doc_id,) in self.db.query(Document.id).filter(
            Document.organization_id == organization_id
        ).all()]
        
        recent_chats = self.db.query(ChatHistory).filter(
            ChatHistory.document_id.in_(org_doc_ids)
        ).order_by(ChatHistory.created_at.desc()).limit(limit).all() if org_doc_ids else []
        
        for chat in recent_chats:
            user = self.db.query(User).filter(User.id == chat.user_id).first()
            doc = self.db.query(Document).filter(Document.id == chat.document_id).first()
            activities.append({
                "type": "chat",
                "description": f"{user.username if user else 'Unknown'} chatted with: {doc.filename if doc else 'Unknown'}",
                "timestamp": chat.created_at,
                "user_id": chat.user_id,
                "user_name": user.username if user else None,
                "document_id": chat.document_id,
                "document_name": doc.filename if doc else None
            })
        
        # Recent user creations
        recent_users = self.db.query(User).filter(
            User.organization_id == organization_id
        ).order_by(User.created_at.desc()).limit(limit).all()
        
        for usr in recent_users:
            activities.append({
                "type": "user_created",
                "description": f"New user created: {usr.username} ({usr.role.value})",
                "timestamp": usr.created_at,
                "user_id": usr.id,
                "user_name": usr.username
            })
        
        # Sort by timestamp and return top N
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
    
    def _get_admin_recent_activity(self, limit: int = 20) -> List[Dict]:
        """Get recent activity system-wide."""
        activities = []
        
        # Recent document uploads
        recent_docs = self.db.query(Document).order_by(
            Document.upload_date.desc()
        ).limit(limit).all()
        
        for doc in recent_docs:
            user = self.db.query(User).filter(User.id == doc.user_id).first()
            org = self.db.query(Organization).filter(Organization.id == doc.organization_id).first()
            activities.append({
                "type": "document_upload",
                "description": f"{user.username if user else 'Unknown'} uploaded: {doc.filename}",
                "timestamp": doc.upload_date,
                "user_id": doc.user_id,
                "user_name": user.username if user else None,
                "organization_id": doc.organization_id,
                "organization_name": org.name if org else None,
                "document_id": doc.id,
                "document_name": doc.filename
            })
        
        # Recent chats
        recent_chats = self.db.query(ChatHistory).order_by(
            ChatHistory.created_at.desc()
        ).limit(limit).all()
        
        for chat in recent_chats:
            user = self.db.query(User).filter(User.id == chat.user_id).first()
            doc = self.db.query(Document).filter(Document.id == chat.document_id).first()
            org = self.db.query(Organization).filter(
                Organization.id == doc.organization_id
            ).first() if doc else None
            
            activities.append({
                "type": "chat",
                "description": f"{user.username if user else 'Unknown'} chatted with: {doc.filename if doc else 'Unknown'}",
                "timestamp": chat.created_at,
                "user_id": chat.user_id,
                "user_name": user.username if user else None,
                "organization_id": doc.organization_id if doc else None,
                "organization_name": org.name if org else None,
                "document_id": chat.document_id,
                "document_name": doc.filename if doc else None
            })
        
        # Recent user creations
        recent_users = self.db.query(User).order_by(
            User.created_at.desc()
        ).limit(limit).all()
        
        for usr in recent_users:
            org = self.db.query(Organization).filter(
                Organization.id == usr.organization_id
            ).first() if usr.organization_id else None
            
            activities.append({
                "type": "user_created",
                "description": f"New user created: {usr.username} ({usr.role.value})",
                "timestamp": usr.created_at,
                "user_id": usr.id,
                "user_name": usr.username,
                "organization_id": usr.organization_id,
                "organization_name": org.name if org else None
            })
        
        # Recent organization creations
        recent_orgs = self.db.query(Organization).order_by(
            Organization.created_at.desc()
        ).limit(limit).all()
        
        for org in recent_orgs:
            activities.append({
                "type": "organization_created",
                "description": f"New organization created: {org.name}",
                "timestamp": org.created_at,
                "organization_id": org.id,
                "organization_name": org.name
            })
        
        # Sort by timestamp and return top N
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]

