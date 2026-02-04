"""Chat service layer."""
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.document import document as document_crud
from app.crud.conversation import conversation as conversation_crud
from app.crud.chat_history import chat_history as chat_history_crud
from app.crud.document_category_description import document_category_description as category_description_crud
from app.models.document import Document
from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_history import ChatHistory
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationUpdate
)
from app.services.rag_chain import RAGChain
from app.services.query_orchestrator import QueryOrchestrator
from app.core.config import settings


class ChatService:
    """Service for chat operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize chat service with database session."""
        self.db = db
        self.document_crud = document_crud
        self.conversation_crud = conversation_crud
        self.chat_history_crud = chat_history_crud
        self.rag_chain = RAGChain()
    
    async def check_rate_limit(self, user: User) -> bool:
        """
        Check if user has remaining chat requests.
        
        Args:
            user: Current user
            
        Returns:
            True if user has remaining chats, False otherwise
        """
        today_count = await self.chat_history_crud.count_today(self.db, user_id=user.id)
        return today_count < user.chat_limit
    
    async def chat_with_document(self, request: ChatRequest, user: User) -> ChatResponse:
        """
        Chat with a document using RAG.
        
        Args:
            request: Chat request with question and document ID
            user: Current user
            
        Returns:
            Chat response with answer and sources
            
        Raises:
            HTTPException: If access denied, rate limited, or processing fails
        """
        # Validate user can chat
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot chat with documents. You must be part of an organization."
            )
        
        # Check rate limit
        if not await self.check_rate_limit(user):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. You have {user.chat_limit} chats per day."
            )
        
        # Get and validate document
        document = await self.document_crud.get(self.db, id=request.document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if not self.document_crud.can_access(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )
        
        # Validate question
        if not request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty"
            )
        
        try:
            # Get or create conversation
            conversation = await self._get_or_create_conversation(
                user=user,
                document=document,
                conversation_id=request.conversation_id
            )

            # Generate title if needed
            if not conversation.title:
                conversation.title = await self._generate_conversation_title(request.question)
                await self.db.flush()

            # Get conversation history
            conversation_history = await self._get_conversation_history(conversation.id)

            # Build system prompt based on user type
            system_prompt = await self._build_system_prompt(user, document)

            # Hybrid pipeline: use orchestrator for structured docs (Excel/CSV/DB), else RAG only
            if getattr(document, "sqlite_path", None):
                orchestrator = QueryOrchestrator(
                    document=document,
                    rag_query_fn=lambda vs, q, **kw: self.rag_chain.query(vs, q, **kw),
                    llm_callable=self.rag_chain._llm_generate,
                )
                result = orchestrator.route_query(
                    request.question,
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                )
            else:
                result = self.rag_chain.query(
                    document.vector_store_path,
                    request.question,
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                )
            
            # Extract token counts
            prompt_tokens = result.get("prompt_tokens", 0)
            completion_tokens = result.get("completion_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens
            
            # Save chat history
            chat_history_dict = {
                "conversation_id": conversation.id,
                "user_id": user.id,
                "document_id": document.id,
                "question": request.question,
                "answer": result["answer"],
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }
            await self.chat_history_crud.create_from_dict(self.db, obj_dict=chat_history_dict)

            # Update user's used tokens
            user.used_tokens = (user.used_tokens or 0) + total_tokens

            # Update conversation timestamp
            conversation.updated_at = datetime.utcnow()

            self.db.add(conversation)
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(conversation)
            await self.db.refresh(user)
            
            return ChatResponse(
                answer=result["answer"],
                source_documents=result["source_documents"],
                conversation_id=conversation.id
            )
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            
            # Provide more user-friendly error messages
            error_message = str(e)
            if "api key" in error_message.lower() or "api_key" in error_message.lower():
                if "expired" in error_message.lower() or "invalid" in error_message.lower():
                    detail = "API key expired or invalid. Please contact the administrator to renew the API keys."
                else:
                    detail = f"API key error: {error_message}"
            elif "embedding" in error_message.lower() or "vector store" in error_message.lower():
                detail = f"Error retrieving document information: {error_message}"
            elif "rate limit" in error_message.lower():
                detail = f"Service temporarily unavailable due to rate limits: {error_message}"
            else:
                detail = f"Error processing chat request: {error_message}"
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail
            )
    
    async def get_chat_history(
        self,
        user: User,
        document_id: Optional[int] = None,
        conversation_id: Optional[int] = None
    ) -> List[ChatHistory]:
        """
        Get chat history for user.
        
        Args:
            user: Current user
            document_id: Optional document filter
            conversation_id: Optional conversation filter
            
        Returns:
            List of chat history entries
        """
        # Validate user can access history
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot access chat history. You must be part of an organization."
            )
        
        if conversation_id:
            conv = await self.conversation_crud.get(self.db, id=conversation_id)
            if not conv or conv.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            doc = await self.document_crud.get(self.db, id=conv.document_id)
            if doc and not self.document_crud.can_access(doc, user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this conversation"
                )

        elif document_id:
            doc = await self.document_crud.get(self.db, id=document_id)
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            if not self.document_crud.can_access(doc, user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this document"
                )
        
        return await self.chat_history_crud.get_by_user(
            self.db,
            user_id=user.id,
            document_id=document_id,
            conversation_id=conversation_id
        )

    async def get_chat_by_id(self, chat_id: int, user: User) -> ChatHistory:
        """
        Get a specific chat history entry.
        
        Args:
            chat_id: Chat history ID
            user: Current user
            
        Returns:
            Chat history entry
        """
        # Validate user can access
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot access chat history. You must be part of an organization."
            )
        
        chat = await self.chat_history_crud.get(self.db, id=chat_id)
        if not chat or chat.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat history not found"
            )
        doc = await self.document_crud.get(self.db, id=chat.document_id)
        if doc and not self.document_crud.can_access(doc, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat history"
            )
        
        return chat
    
    async def create_conversation(self, conversation_data: ConversationCreate, user: User) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            conversation_data: Conversation creation data
            user: Current user
            
        Returns:
            Created conversation
        """
        # Validate user can create conversations
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot create conversations. You must be part of an organization."
            )
        
        document = await self.document_crud.get(self.db, id=conversation_data.document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if not self.document_crud.can_access(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )
        
        conversation_dict = {
            "user_id": user.id,
            "document_id": conversation_data.document_id,
            "title": conversation_data.title
        }
        
        return await self.conversation_crud.create_from_dict(self.db, obj_dict=conversation_dict)

    async def get_conversations(
        self,
        user: User,
        document_id: Optional[int] = None
    ) -> List[Conversation]:
        """
        Get conversations for user.
        
        Args:
            user: Current user
            document_id: Optional document filter
            
        Returns:
            List of conversations
        """
        # Validate user can access conversations
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot access conversations. You must be part of an organization."
            )
        
        if document_id:
            document = await self.document_crud.get(self.db, id=document_id)
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            if not self.document_crud.can_access(document, user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this document"
                )
        
        return await self.conversation_crud.get_by_user(
            self.db,
            user_id=user.id,
            document_id=document_id
        )

    async def get_conversation_by_id(self, conversation_id: int, user: User) -> Conversation:
        """
        Get a specific conversation.
        
        Args:
            conversation_id: Conversation ID
            user: Current user
            
        Returns:
            Conversation
        """
        # Validate user can access
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot access conversations. You must be part of an organization."
            )
        
        conversation = await self.conversation_crud.get(self.db, id=conversation_id)
        if not conversation or conversation.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        doc = await self.document_crud.get(self.db, id=conversation.document_id)
        if doc and not self.document_crud.can_access(doc, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        return conversation

    async def update_conversation(
        self,
        conversation_id: int,
        conversation_data: ConversationUpdate,
        user: User
    ) -> Conversation:
        """
        Update a conversation.
        
        Args:
            conversation_id: Conversation ID
            conversation_data: Update data
            user: Current user
            
        Returns:
            Updated conversation
        """
        # Validate user can update
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot update conversations. You must be part of an organization."
            )
        
        conversation = await self.conversation_crud.get(self.db, id=conversation_id)
        if not conversation or conversation.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        doc = await self.document_crud.get(self.db, id=conversation.document_id)
        if doc and not self.document_crud.can_access(doc, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        if conversation_data.title is not None:
            conversation.title = conversation_data.title
            conversation.updated_at = datetime.utcnow()
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def delete_conversation(self, conversation_id: int, user: User) -> None:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID
            user: Current user
        """
        # Validate user can delete
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot delete conversations. You must be part of an organization."
            )
        
        conversation = await self.conversation_crud.get(self.db, id=conversation_id)
        if not conversation or conversation.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        doc = await self.document_crud.get(self.db, id=conversation.document_id)
        if doc and not self.document_crud.can_access(doc, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        await self.conversation_crud.delete(self.db, id=conversation_id)

    async def _get_or_create_conversation(
        self,
        user: User,
        document: Document,
        conversation_id: Optional[int] = None
    ) -> Conversation:
        """Get existing conversation or create new one."""
        if conversation_id:
            conversation = await self.conversation_crud.get_by_user_and_document(
                self.db,
                user_id=user.id,
                document_id=document.id,
                conversation_id=conversation_id
            )
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found or does not belong to this document"
                )
            return conversation
        conversation_dict = {
            "user_id": user.id,
            "document_id": document.id,
            "title": None
        }
        conversation = await self.conversation_crud.create_from_dict(self.db, obj_dict=conversation_dict)
        await self.db.flush()
        return conversation

    async def _generate_conversation_title(self, question: str) -> str:
        """Generate conversation title from first question."""
        try:
            return self.rag_chain.generate_conversation_title(question)
        except Exception:
            return question[:100] if len(question) > 100 else question

    async def _get_conversation_history(self, conversation_id: int) -> List[dict]:
        """Get last 5 chat history entries for conversation context."""
        recent_chats = await self.chat_history_crud.get_by_conversation(
            self.db,
            conversation_id=conversation_id,
            limit=5
        )
        
        # Reverse to get chronological order (oldest first)
        return [
            {"question": chat.question, "answer": chat.answer}
            for chat in reversed(recent_chats)
        ]

    async def _build_system_prompt(self, user: User, document: Document) -> str:
        """
        Build system prompt based on user type.
        
        For private users: Use user.system_prompt
        For organization users: Combine organization description, category description, and system prompt
        
        Args:
            user: Current user
            document: Document being queried
            
        Returns:
            Complete system prompt string
        """
        # Private users: use their personal system prompt
        if not user.is_organization_user():
            if user.system_prompt:
                return user.system_prompt
            else:
                return "You are a helpful AI assistant that answers questions based on the provided context from documents."
        
        # Organization users: build comprehensive prompt
        prompt_parts = []
        
        # 1. Organization description
        if document.organization and document.organization.description:
            prompt_parts.append(f"Organization Context:\n{document.organization.description}\n")
        
        # 2. Category description
        if document.category:
            category_desc = await category_description_crud.get_by_organization_and_category(
                self.db,
                organization_id=document.organization_id,
                category=document.category
            )
            if category_desc and category_desc.description:
                prompt_parts.append(f"Knowledge Base Category ({document.category.upper()}):\n{category_desc.description}\n")
        
        # 3. System prompt (from organization or default)
        if document.organization and document.organization.system_prompt:
            system_prompt_text = document.organization.system_prompt
        elif user.system_prompt:
            # Fallback to user's system prompt if org doesn't have one
            system_prompt_text = user.system_prompt
        else:
            # Default system prompt
            system_prompt_text = "You are a helpful AI assistant that answers questions based on the provided context from documents."
        
        prompt_parts.append(f"System Instructions:\n{system_prompt_text}")
        
        return "\n".join(prompt_parts)

