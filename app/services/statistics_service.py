"""Statistics service layer for dashboard data."""
from typing import Dict, List
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import user as user_crud
from app.crud.document import document as document_crud
from app.crud.organization import organization as organization_crud
from app.crud.conversation import conversation as conversation_crud
from app.crud.chat_history import chat_history as chat_history_crud
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.organization import Organization
from app.models.conversation import Conversation
from app.models.chat_history import ChatHistory
from app.schemas.statistics import (
    UserStatistics,
    OrganizationStatistics,
    AdminStatistics,
)


class StatisticsService:
    """Service for generating statistics and dashboard data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_statistics(self, user: User) -> UserStatistics:
        """Get statistics for a specific user."""
        total_documents = (
            await self.db.execute(
                select(func.count(Document.id)).where(Document.user_id == user.id)
            )
        ).scalar() or 0
        total_conversations = (
            await self.db.execute(
                select(func.count(Conversation.id)).where(Conversation.user_id == user.id)
            )
        ).scalar() or 0
        total_chats = (
            await self.db.execute(
                select(func.count(ChatHistory.id)).where(ChatHistory.user_id == user.id)
            )
        ).scalar() or 0
        total_tokens = user.used_tokens or 0
        today = datetime.utcnow().date()
        chats_today = (
            await self.db.execute(
                select(func.count(ChatHistory.id)).where(
                    and_(
                        ChatHistory.user_id == user.id,
                        ChatHistory.created_at >= datetime.combine(today, datetime.min.time())
                    )
                )
            )
        ).scalar() or 0
        chats_remaining = max(0, user.chat_limit - chats_today)
        documents_by_category = {}
        if user.is_organization_user() and user.organization_id:
            cat_result = await self.db.execute(
                select(Document.category, func.count(Document.id))
                .where(Document.organization_id == user.organization_id)
                .group_by(Document.category)
            )
            for category, count in cat_result.all():
                if category:
                    documents_by_category[str(category)] = count
        recent_activity = await self._get_user_recent_activity(user.id, limit=10)
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

    async def get_organization_statistics(self, organization_id: int, user: User) -> OrganizationStatistics:
        """Get statistics for an organization."""
        from fastapi import HTTPException, status
        if not user.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = org_result.scalar_one_or_none()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        total_users = (
            await self.db.execute(
                select(func.count(User.id)).where(
                    User.organization_id == organization_id,
                    User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
                )
            )
        ).scalar() or 0
        active_users = (
            await self.db.execute(
                select(func.count(User.id)).where(
                    User.organization_id == organization_id,
                    User.is_active == True,
                    User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
                )
            )
        ).scalar() or 0
        total_documents = (
            await self.db.execute(
                select(func.count(Document.id)).where(Document.organization_id == organization_id)
            )
        ).scalar() or 0
        subq = select(Document.id).where(Document.organization_id == organization_id)
        total_conversations = (
            await self.db.execute(
                select(func.count(Conversation.id)).where(Conversation.document_id.in_(subq))
            )
        ).scalar() or 0
        total_chats = (
            await self.db.execute(
                select(func.count(ChatHistory.id)).where(ChatHistory.document_id.in_(subq))
            )
        ).scalar() or 0
        total_tokens = (
            await self.db.execute(
                select(func.sum(User.used_tokens)).where(User.organization_id == organization_id)
            )
        ).scalar() or 0
        documents_by_category = {}
        cat_result = await self.db.execute(
            select(Document.category, func.count(Document.id))
            .where(Document.organization_id == organization_id)
            .group_by(Document.category)
        )
        for category, count in cat_result.all():
            if category:
                documents_by_category[str(category)] = count
        users_by_role = {}
        role_result = await self.db.execute(
            select(User.role, func.count(User.id))
            .where(User.organization_id == organization_id)
            .group_by(User.role)
        )
        for role, count in role_result.all():
            if role:
                users_by_role[role.value] = count
        recent_activity = await self._get_organization_recent_activity(organization_id, limit=10)
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

    async def get_admin_statistics(self, user: User) -> AdminStatistics:
        """Get system-wide statistics for admin users."""
        from fastapi import HTTPException, status
        if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        total_organizations = (await self.db.execute(select(func.count(Organization.id)))).scalar() or 0
        active_organizations = (
            await self.db.execute(
                select(func.count(Organization.id)).where(Organization.is_active == True)
            )
        ).scalar() or 0
        total_users = (await self.db.execute(select(func.count(User.id)))).scalar() or 0
        active_users = (
            await self.db.execute(select(func.count(User.id)).where(User.is_active == True))
        ).scalar() or 0
        total_documents = (await self.db.execute(select(func.count(Document.id)))).scalar() or 0
        total_conversations = (await self.db.execute(select(func.count(Conversation.id)))).scalar() or 0
        total_chats = (await self.db.execute(select(func.count(ChatHistory.id)))).scalar() or 0
        total_tokens = (await self.db.execute(select(func.sum(User.used_tokens)))).scalar() or 0
        users_by_role = {}
        role_result = await self.db.execute(select(User.role, func.count(User.id)).group_by(User.role))
        for role, count in role_result.all():
            if role:
                users_by_role[role.value] = count
        documents_by_category = {}
        cat_result = await self.db.execute(
            select(Document.category, func.count(Document.id)).group_by(Document.category)
        )
        for category, count in cat_result.all():
            if category:
                documents_by_category[str(category)] = count
        orgs_result = await self.db.execute(select(Organization))
        organizations = list(orgs_result.scalars().all())
        uc_result = await self.db.execute(
            select(User.organization_id, func.count(User.id))
            .where(
                User.organization_id.isnot(None),
                User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
            )
            .group_by(User.organization_id)
        )
        user_counts = {row[0]: row[1] for row in uc_result.all()}
        auc_result = await self.db.execute(
            select(User.organization_id, func.count(User.id))
            .where(
                User.organization_id.isnot(None),
                User.is_active == True,
                User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
            )
            .group_by(User.organization_id)
        )
        active_user_counts = {row[0]: row[1] for row in auc_result.all()}
        dc_result = await self.db.execute(
            select(Document.organization_id, func.count(Document.id))
            .group_by(Document.organization_id)
        )
        doc_counts = {row[0]: row[1] for row in dc_result.all()}
        token_result = await self.db.execute(
            select(User.organization_id, func.sum(User.used_tokens))
            .where(User.organization_id.isnot(None))
            .group_by(User.organization_id)
        )
        token_counts = {row[0]: row[1] for row in token_result.all()}
        organizations_stats = []
        for org in organizations:
            doc_ids_result = await self.db.execute(
                select(Document.id).where(Document.organization_id == org.id)
            )
            org_doc_ids = [row[0] for row in doc_ids_result.all()]
            org_conversations = (
                await self.db.execute(
                    select(func.count(Conversation.id)).where(
                        Conversation.document_id.in_(org_doc_ids)
                    )
                )
            ).scalar() or 0 if org_doc_ids else 0
            org_chats = (
                await self.db.execute(
                    select(func.count(ChatHistory.id)).where(
                        ChatHistory.document_id.in_(org_doc_ids)
                    )
                )
            ).scalar() or 0 if org_doc_ids else 0
            org_docs_by_category = {}
            org_cat_result = await self.db.execute(
                select(Document.category, func.count(Document.id))
                .where(Document.organization_id == org.id)
                .group_by(Document.category)
            )
            for category, count in org_cat_result.all():
                if category:
                    org_docs_by_category[str(category)] = count
            org_users_by_role = {}
            org_role_result = await self.db.execute(
                select(User.role, func.count(User.id))
                .where(User.organization_id == org.id)
                .group_by(User.role)
            )
            for role, count in org_role_result.all():
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
                recent_activity=[]
            ))
        recent_activity = await self._get_admin_recent_activity(limit=20)
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

    async def _get_user_recent_activity(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent activity for a user."""
        activities = []
        docs_result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.upload_date.desc())
            .limit(limit)
        )
        recent_docs = list(docs_result.scalars().all())
        for doc in recent_docs:
            activities.append({
                "type": "document_upload",
                "description": f"Uploaded document: {doc.filename}",
                "timestamp": doc.upload_date,
                "document_id": doc.id,
                "document_name": doc.filename
            })
        chats_result = await self.db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        recent_chats = list(chats_result.scalars().all())
        for chat in recent_chats:
            doc_result = await self.db.execute(select(Document).where(Document.id == chat.document_id))
            doc = doc_result.scalar_one_or_none()
            activities.append({
                "type": "chat",
                "description": f"Chatted with document: {doc.filename if doc else 'Unknown'}",
                "timestamp": chat.created_at,
                "document_id": chat.document_id,
                "document_name": doc.filename if doc else None
            })
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]

    async def _get_organization_recent_activity(self, organization_id: int, limit: int = 10) -> List[Dict]:
        """Get recent activity for an organization."""
        activities = []
        docs_result = await self.db.execute(
            select(Document)
            .where(Document.organization_id == organization_id)
            .order_by(Document.upload_date.desc())
            .limit(limit)
        )
        recent_docs = list(docs_result.scalars().all())
        for doc in recent_docs:
            user_result = await self.db.execute(select(User).where(User.id == doc.user_id))
            user = user_result.scalar_one_or_none()
            activities.append({
                "type": "document_upload",
                "description": f"{user.username if user else 'Unknown'} uploaded: {doc.filename}",
                "timestamp": doc.upload_date,
                "user_id": doc.user_id,
                "user_name": user.username if user else None,
                "document_id": doc.id,
                "document_name": doc.filename
            })
        doc_ids_result = await self.db.execute(
            select(Document.id).where(Document.organization_id == organization_id)
        )
        org_doc_ids = [row[0] for row in doc_ids_result.all()]
        if org_doc_ids:
            chats_result = await self.db.execute(
                select(ChatHistory)
                .where(ChatHistory.document_id.in_(org_doc_ids))
                .order_by(ChatHistory.created_at.desc())
                .limit(limit)
            )
            recent_chats = list(chats_result.scalars().all())
            for chat in recent_chats:
                user_result = await self.db.execute(select(User).where(User.id == chat.user_id))
                user = user_result.scalar_one_or_none()
                doc_result = await self.db.execute(select(Document).where(Document.id == chat.document_id))
                doc = doc_result.scalar_one_or_none()
                activities.append({
                    "type": "chat",
                    "description": f"{user.username if user else 'Unknown'} chatted with: {doc.filename if doc else 'Unknown'}",
                    "timestamp": chat.created_at,
                    "user_id": chat.user_id,
                    "user_name": user.username if user else None,
                    "document_id": chat.document_id,
                    "document_name": doc.filename if doc else None
                })
        users_result = await self.db.execute(
            select(User)
            .where(User.organization_id == organization_id)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        recent_users = list(users_result.scalars().all())
        for usr in recent_users:
            activities.append({
                "type": "user_created",
                "description": f"New user created: {usr.username} ({usr.role.value})",
                "timestamp": usr.created_at,
                "user_id": usr.id,
                "user_name": usr.username
            })
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]

    async def _get_admin_recent_activity(self, limit: int = 20) -> List[Dict]:
        """Get recent activity system-wide."""
        activities = []
        docs_result = await self.db.execute(
            select(Document).order_by(Document.upload_date.desc()).limit(limit)
        )
        recent_docs = list(docs_result.scalars().all())
        for doc in recent_docs:
            user_result = await self.db.execute(select(User).where(User.id == doc.user_id))
            user = user_result.scalar_one_or_none()
            org_result = await self.db.execute(select(Organization).where(Organization.id == doc.organization_id))
            org = org_result.scalar_one_or_none()
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
        chats_result = await self.db.execute(
            select(ChatHistory).order_by(ChatHistory.created_at.desc()).limit(limit)
        )
        recent_chats = list(chats_result.scalars().all())
        for chat in recent_chats:
            user_result = await self.db.execute(select(User).where(User.id == chat.user_id))
            user = user_result.scalar_one_or_none()
            doc_result = await self.db.execute(select(Document).where(Document.id == chat.document_id))
            doc = doc_result.scalar_one_or_none()
            org = None
            if doc:
                org_result = await self.db.execute(
                    select(Organization).where(Organization.id == doc.organization_id)
                )
                org = org_result.scalar_one_or_none()
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
        users_result = await self.db.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        recent_users = list(users_result.scalars().all())
        for usr in recent_users:
            org = None
            if usr.organization_id:
                org_result = await self.db.execute(
                    select(Organization).where(Organization.id == usr.organization_id)
                )
                org = org_result.scalar_one_or_none()
            activities.append({
                "type": "user_created",
                "description": f"New user created: {usr.username} ({usr.role.value})",
                "timestamp": usr.created_at,
                "user_id": usr.id,
                "user_name": usr.username,
                "organization_id": usr.organization_id,
                "organization_name": org.name if org else None
            })
        orgs_result = await self.db.execute(
            select(Organization).order_by(Organization.created_at.desc()).limit(limit)
        )
        recent_orgs = list(orgs_result.scalars().all())
        for org in recent_orgs:
            activities.append({
                "type": "organization_created",
                "description": f"New organization created: {org.name}",
                "timestamp": org.created_at,
                "organization_id": org.id,
                "organization_name": org.name
            })
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
