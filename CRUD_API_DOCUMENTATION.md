# Comprehensive API Documentation

## Overview

This document describes all API endpoints available in the multi-tenant chatbot system. The system follows a layered architecture:

**Architecture**: Routes → Service Layer → CRUD Layer → Database Models

All endpoints use service classes for business logic, ensuring separation of concerns and maintainability.

## Base URL

All endpoints are prefixed with `/api/v1`

## Authentication

Most endpoints require authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## Authentication API (`/api/v1/auth`)

### Signup
```
POST /api/v1/auth/signup
```
- **Access**: Public
- **Body**: `UserSignup`
  ```json
  {
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password"
  }
  ```
- **Returns**: `UserResponse` (creates a private USER role)
- **Notes**: Creates a private user (not associated with any organization)

### Login
```
POST /api/v1/auth/login
```
- **Access**: Public
- **Body**: `UserLogin`
  ```json
  {
    "email": "john@example.com",
    "password": "secure_password"
  }
  ```
- **Returns**: `Token` (access_token, refresh_token, token_type)

### Get Current User
```
GET /api/v1/auth/me
```
- **Access**: Authenticated users
- **Returns**: `UserResponse`

### Refresh Token
```
POST /api/v1/auth/refresh
```
- **Access**: Public
- **Body**: `RefreshTokenRequest`
  ```json
  {
    "refresh_token": "refresh_token_string"
  }
  ```
- **Returns**: `Token` (new access and refresh tokens)

### Update System Prompt
```
PATCH /api/v1/auth/me/system-prompt
```
- **Access**: Authenticated users
- **Body**: `SystemPromptUpdate`
  ```json
  {
    "system_prompt": "You are a helpful assistant."
  }
  ```
- **Returns**: `UserResponse`

---

## User Management API (`/api/v1/users`)

### Create User
```
POST /api/v1/users
```
- **Access**: SuperAdmin, Admin
- **Body**: `UserCreate`
  ```json
  {
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password",
    "role": "org_user",
    "organization_id": 1,
    "chat_limit": 10
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - Admins cannot create SuperAdmin or Admin users
  - For ORG_ADMIN and ORG_USER roles, organization_id is required
  - For USER role (private), organization_id must be null

### List Users
```
GET /api/v1/users?organization_id=1&role=org_user&skip=0&limit=100
```
- **Access**: All authenticated users (filtered by role)
- **Query Parameters**:
  - `organization_id` (optional): Filter by organization
  - `role` (optional): Filter by role (SUPER_ADMIN, ADMIN, ORG_ADMIN, ORG_USER, USER)
  - `skip` (default: 0): Pagination offset
  - `limit` (default: 100, max: 100): Pagination limit
- **Returns**: `List[UserResponse]`
- **Access Control**:
  - SuperAdmin/Admin: See all users
  - OrgAdmin: See users in their organization
  - OrgUser: See only themselves
  - Private User: See only themselves

### Get User
```
GET /api/v1/users/{user_id}
```
- **Access**: Based on role and organization membership
- **Returns**: `UserResponse`
- **Access Control**: Same as list users

### Update User
```
PATCH /api/v1/users/{user_id}
```
- **Access**: SuperAdmin, Admin
- **Body**: `UserUpdate` (all fields optional)
  ```json
  {
    "username": "new_username",
    "email": "new_email@example.com",
    "role": "org_admin",
    "organization_id": 1,
    "chat_limit": 20,
    "is_active": true,
    "system_prompt": "Custom prompt"
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - Admins cannot modify SuperAdmin or Admin users
  - Role changes must respect organization requirements

### Delete User
```
DELETE /api/v1/users/{user_id}
```
- **Access**: SuperAdmin only
- **Returns**: 204 No Content
- **Notes**: Cannot delete your own account

### Update User Password
```
PATCH /api/v1/users/{user_id}/password
```
- **Access**: SuperAdmin, Admin
- **Body**: `PasswordUpdate`
  ```json
  {
    "new_password": "new_secure_password"
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: Admins cannot change passwords for SuperAdmin or Admin users

### Update User Chat Limit
```
PATCH /api/v1/users/{user_id}/chat-limit
```
- **Access**: SuperAdmin, Admin
- **Body**: `ChatLimitUpdate`
  ```json
  {
    "chat_limit": 50
  }
  ```
- **Returns**: `UserResponse`

### Toggle User Active Status
```
PATCH /api/v1/users/{user_id}/activate
```
- **Access**: SuperAdmin, Admin
- **Returns**: `UserResponse`
- **Notes**: 
  - Cannot deactivate your own account
  - Admins cannot deactivate SuperAdmin or Admin users

---

## Organization Management API (`/api/v1/organizations`)

### Create Organization
```
POST /api/v1/organizations
```
- **Access**: SuperAdmin, Admin
- **Body**: `OrganizationCreate`
  ```json
  {
    "name": "Acme Corporation",
    "description": "Main organization",
    "is_active": true,
    "admin_user": {
      "username": "org_admin",
      "email": "admin@acme.com",
      "password": "secure_password123"
    }
  }
  ```
- **Returns**: `OrganizationResponse`
- **Notes**: Automatically creates an ORG_ADMIN user for the organization

### List Organizations
```
GET /api/v1/organizations?skip=0&limit=100
```
- **Access**: All authenticated users (filtered by role)
- **Query Parameters**:
  - `skip` (default: 0): Pagination offset
  - `limit` (default: 100, max: 100): Pagination limit
- **Returns**: `List[OrganizationResponse]`
- **Access Control**:
  - SuperAdmin/Admin: See all organizations
  - OrgAdmin/OrgUser: See only their organization
  - Private User: Cannot see any organizations

### Get Organization
```
GET /api/v1/organizations/{organization_id}
```
- **Access**: Users with access to the organization
- **Returns**: `OrganizationResponse`

### Update Organization
```
PATCH /api/v1/organizations/{organization_id}
```
- **Access**: SuperAdmin, Admin
- **Body**: `OrganizationUpdate`
  ```json
  {
    "name": "Updated Name",
    "description": "Updated description",
    "is_active": false
  }
  ```
- **Returns**: `OrganizationResponse`

### Delete Organization
```
DELETE /api/v1/organizations/{organization_id}
```
- **Access**: SuperAdmin only
- **Returns**: 204 No Content

## Organization User Management (`/api/v1/organizations/{organization_id}/users`)

### List Organization Users
```
GET /api/v1/organizations/{organization_id}/users?role=org_user&skip=0&limit=100
```
- **Access**: Users with access to the organization
- **Query Parameters**:
  - `role` (optional): Filter by role (ORG_ADMIN, ORG_USER)
  - `skip`, `limit`: Pagination
- **Returns**: `List[UserResponse]`

### Create Organization User
```
POST /api/v1/organizations/{organization_id}/users
```
- **Access**: OrgAdmin, Admin, SuperAdmin
- **Body**: `UserCreate` (organization_id will be set automatically)
  ```json
  {
    "username": "org_user",
    "email": "org_user@example.com",
    "password": "password",
    "role": "org_user",
    "chat_limit": 5
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - OrgAdmins can only create ORG_USER role
  - Organization ID is automatically set
  - Only ORG_ADMIN and ORG_USER roles can be created in organizations

---

## Document Management API (`/api/v1/documents`)

### Upload Document
```
POST /api/v1/documents/upload?organization_id=1&category=GENERAL
```
- **Access**: Organization users (ORG_ADMIN, ORG_USER)
- **Query Parameters**:
  - `organization_id` (optional): Organization ID (defaults to user's organization)
  - `category` (optional): Document category (GENERAL, HR, SALES, LEGAL, OPS) - default: GENERAL
- **Body**: Multipart form data with file
- **Supported Formats**: PDF, DOCX, TXT, HTML
- **Returns**: `UploadResponse`
  ```json
  {
    "document_id": 1,
    "filename": "document.pdf",
    "message": "Document uploaded and processed successfully",
    "chunk_count": 25
  }
  ```
- **Notes**: 
  - Private users (USER role) cannot upload documents
  - Documents are scoped to organizations

### List Documents
```
GET /api/v1/documents?organization_id=1&category=HR
```
- **Access**: Organization users (ORG_ADMIN, ORG_USER)
- **Query Parameters**:
  - `organization_id` (optional): Filter by organization
  - `category` (optional): Filter by category
- **Returns**: `List[DocumentInfo]`
- **Notes**: Private users cannot access documents

### Get Document
```
GET /api/v1/documents/{document_id}
```
- **Access**: Organization users with access to the document's organization
- **Returns**: `DocumentInfo`

### Delete Document
```
DELETE /api/v1/documents/{document_id}
```
- **Access**: Document owner, OrgAdmin (in same org), Admin, SuperAdmin
- **Returns**: 204 No Content
- **Notes**: 
  - Deletes document, vector store, and uploaded file
  - Private users cannot delete documents

---

## Chat API (`/api/v1/chat`)

### Chat with Document
```
POST /api/v1/chat
```
- **Access**: Organization users (ORG_ADMIN, ORG_USER)
- **Body**: `ChatRequest`
  ```json
  {
    "document_id": 1,
    "question": "What is the main topic?",
    "conversation_id": null
  }
  ```
- **Returns**: `ChatResponse`
  ```json
  {
    "answer": "The main topic is...",
    "source_documents": ["chunk1", "chunk2"],
    "conversation_id": 1
  }
  ```
- **Notes**: 
  - Rate limited based on user's `chat_limit` (per day)
  - Private users cannot chat with documents
  - If `conversation_id` is null, a new conversation is created

### Get Chat History
```
GET /api/v1/chat/history?document_id=1&conversation_id=1
```
- **Access**: Organization users
- **Query Parameters**:
  - `document_id` (optional): Filter by document
  - `conversation_id` (optional): Filter by conversation
- **Returns**: `List[ChatHistoryResponse]` (sorted ascending by created_at)
- **Notes**: Private users cannot access chat history

### Get Chat by ID
```
GET /api/v1/chat/history/{chat_id}
```
- **Access**: Organization users (owner of the chat)
- **Returns**: `ChatHistoryResponse`

## Conversation Management (`/api/v1/chat/conversations`)

### Create Conversation
```
POST /api/v1/chat/conversations
```
- **Access**: Organization users
- **Body**: `ConversationCreate`
  ```json
  {
    "document_id": 1,
    "title": "Discussion about policies"
  }
  ```
- **Returns**: `ConversationResponse`
- **Notes**: Private users cannot create conversations

### List Conversations
```
GET /api/v1/chat/conversations?document_id=1
```
- **Access**: Organization users
- **Query Parameters**:
  - `document_id` (optional): Filter by document
- **Returns**: `List[ConversationResponse]` (sorted descending by created_at)
- **Notes**: Private users cannot access conversations

### Get Conversation
```
GET /api/v1/chat/conversations/{conversation_id}
```
- **Access**: Organization users (owner of the conversation)
- **Returns**: `ConversationResponse`

### Update Conversation
```
PATCH /api/v1/chat/conversations/{conversation_id}
```
- **Access**: Organization users (owner of the conversation)
- **Body**: `ConversationUpdate`
  ```json
  {
    "title": "Updated title"
  }
  ```
- **Returns**: `ConversationResponse`

### Delete Conversation
```
DELETE /api/v1/chat/conversations/{conversation_id}
```
- **Access**: Organization users (owner of the conversation)
- **Returns**: 204 No Content
- **Notes**: Deletes conversation and all associated chat history

---

## Admin API (`/api/v1/admin`)

### List SuperAdmins
```
GET /api/v1/admin/superadmins?skip=0&limit=100
```
- **Access**: SuperAdmin only
- **Returns**: `List[UserResponse]`

### Create SuperAdmin
```
POST /api/v1/admin/superadmins
```
- **Access**: SuperAdmin only
- **Body**: `UserCreate` (role will be forced to SUPER_ADMIN)
  ```json
  {
    "username": "superadmin2",
    "email": "superadmin2@example.com",
    "password": "secure_password",
    "chat_limit": 1000
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - Role is automatically set to SUPER_ADMIN
  - Organization ID is set to null

### List Admins
```
GET /api/v1/admin/admins?skip=0&limit=100
```
- **Access**: Admin, SuperAdmin
- **Returns**: `List[UserResponse]`

### Create Admin
```
POST /api/v1/admin/admins
```
- **Access**: SuperAdmin only
- **Body**: `UserCreate` (role will be forced to ADMIN)
  ```json
  {
    "username": "admin2",
    "email": "admin2@example.com",
    "password": "secure_password",
    "chat_limit": 500
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: Role is automatically set to ADMIN

---

## Role-Based Access Summary

### SuperAdmin
- ✅ Full CRUD on all entities
- ✅ Can create SuperAdmin and Admin users
- ✅ Can delete any user
- ✅ Can manage all organizations
- ✅ Can access all documents and chats

### Admin
- ✅ Can create ORG_ADMIN, ORG_USER, USER (private)
- ❌ Cannot create/modify SuperAdmin or Admin users
- ✅ Can manage organizations
- ✅ Can see all users
- ✅ Can access all documents and chats

### OrgAdmin
- ✅ Can create ORG_USER in their organization
- ✅ Can manage users in their organization
- ✅ Can upload/manage documents in their organization
- ✅ Can chat with documents in their organization
- ❌ Cannot create ORG_ADMIN, ADMIN, SUPER_ADMIN
- ❌ Cannot access other organizations

### OrgUser
- ✅ Can upload/view documents in their organization
- ✅ Can chat with documents in their organization
- ✅ Can see only themselves
- ❌ Cannot manage other users
- ❌ Cannot access other organizations

### User (Private)
- ✅ Can see only themselves
- ✅ Can update their own system prompt
- ❌ Cannot access documents
- ❌ Cannot chat with documents
- ❌ Cannot be assigned to organizations
- ❌ Cannot manage other users

---

## User Roles

### SUPER_ADMIN
- Top-level administrator
- Full system access
- Not associated with any organization

### ADMIN
- System administrator (under SuperAdmin)
- Can manage organizations
- Not necessarily associated with an organization

### ORG_ADMIN
- Organization administrator
- Manages users and documents within their organization
- Must be associated with an organization

### ORG_USER
- Regular user within an organization
- Can upload documents and chat
- Must be associated with an organization

### USER
- Private user (not in any organization)
- Limited access (cannot use document/chat features)
- Not associated with any organization

---

## Example Workflows

### Creating a Complete Organization Structure

1. **Create Organization** (SuperAdmin/Admin):
   ```bash
   POST /api/v1/organizations
   {
     "name": "Tech Corp",
     "description": "Technology company",
     "is_active": true,
     "admin_user": {
       "username": "org_admin",
       "email": "admin@techcorp.com",
       "password": "secure_password123"
     }
   }
   ```
   This automatically creates an ORG_ADMIN user.

2. **Create Organization Users** (OrgAdmin/Admin/SuperAdmin):
   ```bash
   POST /api/v1/organizations/1/users
   {
     "username": "engineer1",
     "email": "engineer1@techcorp.com",
     "password": "password",
     "role": "org_user",
     "chat_limit": 10
   }
   ```

3. **Upload Document** (OrgAdmin/OrgUser):
   ```bash
   POST /api/v1/documents/upload?category=GENERAL
   Content-Type: multipart/form-data
   file: <document.pdf>
   ```

4. **Chat with Document** (OrgAdmin/OrgUser):
   ```bash
   POST /api/v1/chat
   {
     "document_id": 1,
     "question": "What is this document about?"
   }
   ```

---

## Error Responses

All endpoints return standard HTTP status codes:
- `200 OK`: Successful GET/PATCH
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists (e.g., duplicate email/username)
- `429 Too Many Requests`: Rate limit exceeded

---

## Architecture Notes

The API follows a layered architecture:

1. **Routes** (`app/api/v1/*`): Handle HTTP requests/responses
2. **Services** (`app/services/*_service.py`): Business logic layer
3. **CRUD** (`app/crud/*`): Data access layer
4. **Models** (`app/models/*`): Database models

This separation ensures:
- **Maintainability**: Business logic is centralized
- **Testability**: Services can be tested independently
- **Scalability**: Easy to add new features
- **Consistency**: Standardized patterns across codebase
