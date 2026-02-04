# API Documentation — Full Flow for UI Implementation

This document describes all API endpoints, request/response shapes, and the **end-to-end flow** so you can implement the UI correctly.

---

## Table of Contents

1. [Base URL & Authentication](#base-url--authentication)
2. [High-Level Flow (UI Order)](#high-level-flow-ui-order)
3. [Authentication API](#authentication-api)
4. [User Management API](#user-management-api)
5. [Organization API](#organization-api)
6. [Category Descriptions API](#category-descriptions-api)
7. [Document API (Upload & List)](#document-api-upload--list)
8. [Chat API (Conversations & Messages)](#chat-api-conversations--messages)
9. [Statistics API](#statistics-api)
10. [Admin API](#admin-api)
11. [Roles & Access](#roles--access)
12. [Error Responses](#error-responses)
13. [Document & Chat Behavior](#document--chat-behavior)

---

## Base URL & Authentication

- **Base URL**: All endpoints are under `/api/v1` (e.g. `https://chatapi.techtattava.com/api/v1`).
- **Auth**: Send the JWT in the header:
  ```http
  Authorization: Bearer <access_token>
  ```
- **Login** returns `access_token` and `refresh_token`. Use **refresh** when the access token expires (see [Authentication API](#authentication-api)).

---

## High-Level Flow (UI Order)

Use this order when building the UI:

1. **Auth**  
   - **Signup** (optional) → creates a **private user** (no org).  
   - **Login** → get `access_token`, `refresh_token`.  
   - **GET /auth/me** → get current user (role, `organization_id`, `chat_limit`, etc.).

2. **Organizations** (if user is org member or admin)  
   - **GET /organizations** → list orgs the user can see.  
   - **GET /organizations/{id}** → org details (name, description, system_prompt).  
   - SuperAdmin/Admin: **POST /organizations** to create org (with first org admin user).

3. **Organization users** (OrgAdmin / Admin / SuperAdmin)  
   - **GET /organizations/{id}/users** → list users in org.  
   - **POST /organizations/{id}/users** → add user to org (role `org_admin` or `org_user`).

4. **Categories** (optional, for better prompts)  
   - **GET /organizations/{id}/categories** → list category descriptions.  
   - **POST/PATCH/DELETE** to manage category descriptions (e.g. "HR", "Sales").

5. **Documents**  
   - **POST /documents/upload** → upload file (PDF, DOCX, TXT, HTML, MD, or Excel, CSV, SQLite).  
   - **GET /documents** → list documents (optional filters: `organization_id`, `category`).  
   - **GET /documents/{id}** → single document (includes `sqlite_path` if structured).  
   - **DELETE /documents/{id}** → delete document and its artifacts.

6. **Chat**  
   - **POST /chat** → send a question for a document (creates or continues a conversation).  
   - **GET /chat/conversations** → list conversations (optional `document_id`).  
   - **GET /chat/conversations/{id}** → one conversation.  
   - **GET /chat/history** → list chat messages (optional `document_id`, `conversation_id`).

7. **Statistics**  
   - **GET /statistics/user** → current user stats (documents, chats, limit, etc.).  
   - **GET /statistics/organization/{id}** → org stats (OrgAdmin/Admin/SuperAdmin).  
   - **GET /statistics/admin** → global stats (Admin/SuperAdmin only).

8. **Admin** (SuperAdmin/Admin only)  
   - **GET/POST /admin/superadmins**, **GET/POST /admin/admins** as needed.

---

## Authentication API

**Prefix**: `/api/v1/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/signup` | No | Register a **private user** (no organization). |
| POST | `/login` | No | Login; returns tokens. |
| GET | `/me` | Yes | Current user profile. |
| POST | `/refresh` | No | New tokens using refresh_token. |
| PATCH | `/me/system-prompt` | Yes | Update current user's system prompt (for private users). |

### POST /auth/signup

- **Body**:
  ```json
  {
    "username": "johndoe",
    "email": "john@example.com",
    "password": "secure_password"
  }
  ```
- **Response**: `201` + `UserResponse` (private user created).

### POST /auth/login

- **Body**:
  ```json
  {
    "email": "john@example.com",
    "password": "secure_password"
  }
  ```
- **Response**: `200` + `Token`:
  ```json
  {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
  ```

### GET /auth/me

- **Response**: `200` + `UserResponse` (id, username, email, role, organization_id, chat_limit, system_prompt, used_tokens, is_active, is_admin, created_at).

### POST /auth/refresh

- **Body**:
  ```json
  {
    "refresh_token": "eyJ..."
  }
  ```
- **Response**: `200` + `Token` (new access_token and refresh_token).

### PATCH /auth/me/system-prompt

- **Body**:
  ```json
  {
    "system_prompt": "You are a helpful assistant."
  }
  ```
- **Response**: `200` + `UserResponse`.

---

## User Management API

**Prefix**: `/api/v1/users`  
**Access**: Depends on role (see [Roles & Access](#roles--access)).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Create user (SuperAdmin/Admin). |
| GET | `/` | List users (query: `organization_id`, `role`, `skip`, `limit`). |
| GET | `/{user_id}` | Get one user. |
| PATCH | `/{user_id}` | Update user. |
| DELETE | `/{user_id}` | Delete user (SuperAdmin only). |
| PATCH | `/{user_id}/password` | Change password. |
| PATCH | `/{user_id}/chat-limit` | Set chat limit. |
| PATCH | `/{user_id}/activate` | Toggle is_active. |

### POST /users

- **Body** (`UserCreate`):
  ```json
  {
    "username": "jane",
    "email": "jane@example.com",
    "password": "password",
    "role": "org_user",
    "organization_id": 1,
    "chat_limit": 10
  }
  ```
  - For **private user**: `role`: `"user"`, `organization_id`: `null`.  
  - For org users: `role`: `"org_admin"` or `"org_user"`, `organization_id` required.
- **Response**: `201` + `UserResponse`.

### GET /users

- **Query**: `organization_id` (optional), `role` (optional), `skip` (default 0), `limit` (default 100, max 100).
- **Response**: `200` + array of `UserResponse`.

### GET /users/{user_id}

- **Response**: `200` + `UserResponse`.

### PATCH /users/{user_id}

- **Body** (`UserUpdate`, all optional): `username`, `email`, `is_active`, `role`, `organization_id`, `chat_limit`, `system_prompt`.
- **Response**: `200` + `UserResponse`.

### DELETE /users/{user_id}

- **Response**: `204 No Content`. SuperAdmin only; cannot delete self.

### PATCH /users/{user_id}/password

- **Body**: `{ "new_password": "new_secret" }`
- **Response**: `200` + `UserResponse`.

### PATCH /users/{user_id}/chat-limit

- **Body**: `{ "chat_limit": 50 }`
- **Response**: `200` + `UserResponse`.

### PATCH /users/{user_id}/activate

- **Response**: `200` + `UserResponse` (toggles `is_active`). Cannot deactivate self.

---

## Organization API

**Prefix**: `/api/v1/organizations`

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/` | SuperAdmin, Admin | Create organization (+ first org admin user). |
| GET | `/` | All (filtered by role) | List organizations. |
| GET | `/{organization_id}` | Org access | Get one organization. |
| PATCH | `/{organization_id}` | SuperAdmin, Admin | Update organization. |
| DELETE | `/{organization_id}` | SuperAdmin only | Delete organization and its artifacts. |
| GET | `/{organization_id}/users` | Org access | List users in org. |
| POST | `/{organization_id}/users` | OrgAdmin, Admin, SuperAdmin | Create user in org. |

### POST /organizations

- **Body** (`OrganizationCreate`):
  ```json
  {
    "name": "Acme Corp",
    "description": "Main organization",
    "system_prompt": "You are a helpful AI for Acme. Be professional.",
    "is_active": true,
    "admin_user": {
      "username": "org_admin",
      "email": "admin@acme.com",
      "password": "secure_password123"
    }
  }
  ```
- **Response**: `201` + `OrganizationResponse`. Creates an **ORG_ADMIN** user for the org.

### GET /organizations

- **Query**: `skip` (default 0), `limit` (default 100, max 100).
- **Response**: `200` + array of `OrganizationResponse`.

### GET /organizations/{organization_id}

- **Response**: `200` + `OrganizationResponse` (id, name, description, system_prompt, is_active, created_at, updated_at).

### PATCH /organizations/{organization_id}

- **Body** (all optional): `name`, `description`, `system_prompt`, `is_active`.
- **Response**: `200` + `OrganizationResponse`.

### DELETE /organizations/{organization_id}

- **Response**: `204 No Content`. Removes org and all its artifacts (uploads, vector stores, structured data).

### GET /organizations/{organization_id}/users

- **Query**: `role` (optional), `skip`, `limit`.
- **Response**: `200` + array of `UserResponse`.

### POST /organizations/{organization_id}/users

- **Body**: Same as `UserCreate` but **omit** `organization_id` (set automatically). Use `role`: `"org_admin"` or `"org_user"`.
- **Response**: `201` + `UserResponse`.

---

## Category Descriptions API

**Prefix**: `/api/v1/organizations/{organization_id}/categories`  
Categories are free-text labels (e.g. "HR", "Sales") with optional descriptions used when building AI prompts for that org.

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/organizations/{organization_id}/categories` | SuperAdmin, Admin, OrgAdmin | Create category description. |
| GET | `/organizations/{organization_id}/categories` | Org access | List category descriptions. |
| GET | `/organizations/{organization_id}/categories/{category}` | Org access | Get one category (category = name string). |
| PATCH | `/organizations/{organization_id}/categories/{category}` | SuperAdmin, Admin, OrgAdmin | Update description. |
| DELETE | `/organizations/{organization_id}/categories/{category}` | SuperAdmin, Admin, OrgAdmin | Delete category description. |

### POST .../categories

- **Body**:
  ```json
  {
    "category": "HR",
    "description": "Human Resources documents: policies, handbooks, procedures."
  }
  ```
- **Response**: `201` + category object (id, organization_id, category, description, created_at, updated_at).

### GET .../categories

- **Query**: `skip`, `limit`.
- **Response**: `200` + array of category objects.

### GET .../categories/{category}

- **Response**: `200` + single category object. `{category}` is the exact name (e.g. `HR`).

### PATCH .../categories/{category}

- **Body**: `{ "description": "Updated description" }`
- **Response**: `200` + category object.

### DELETE .../categories/{category}

- **Response**: `204 No Content`. Documents with that category keep the category; only the description is removed.

---

## Document API (Upload & List)

**Prefix**: `/api/v1/documents`  
**Access**: Only **organization users** (ORG_ADMIN, ORG_USER). Private users cannot upload or list documents.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload a file (multipart). |
| GET | `/` | List documents. |
| GET | `/{document_id}` | Get one document. |
| DELETE | `/{document_id}` | Delete document and its artifacts. |

### POST /documents/upload

- **Query**:
  - `organization_id` (optional): Defaults to current user's organization.
  - `category` (optional): Free-text category (e.g. "HR", "Sales").
- **Body**: **multipart/form-data** with one file field (e.g. `file`).

**Supported file types**:

- **Unstructured (RAG only)**: PDF, DOCX, TXT, HTML, MD.  
- **Structured (Hybrid SQL + RAG)**: Excel (xlsx, xls), CSV, SQLite (db, sqlite). For these, the backend creates a SQLite DB and row-level text for RAG; chat uses the **orchestrator** (SQL vs RAG) for that document.

**Response**: `201` + `UploadResponse`:
```json
{
  "document_id": 1,
  "filename": "report.pdf",
  "message": "Document uploaded and processed successfully",
  "chunk_count": 25
}
```

**UI**: Use `FormData` / `multipart/form-data`; attach the file and optionally send `organization_id` and `category` as query params.

### GET /documents

- **Query**: `organization_id` (optional), `category` (optional).
- **Response**: `200` + array of `DocumentInfo`:
  - `id`, `filename`, `file_type`, `organization_id`, `category`, `version`, `upload_date`, `file_size`, `chunk_count`, `sqlite_path` (set for Excel/CSV/DB; use to show “Hybrid” or “SQL+RAG” in UI).

### GET /documents/{document_id}

- **Response**: `200` + `DocumentInfo`.

### DELETE /documents/{document_id}

- **Response**: `204 No Content`. Deletes DB record, vector store, upload file, and SQLite file (if structured).

---

## Chat API (Conversations & Messages)

**Prefix**: `/api/v1/chat`  
**Access**: Only **organization users**. Private users cannot chat.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Send a question (chat with document). |
| GET | `/history` | List chat history entries. |
| GET | `/history/{chat_id}` | Get one chat entry. |
| POST | `/conversations` | Create a conversation. |
| GET | `/conversations` | List conversations. |
| GET | `/conversations/{conversation_id}` | Get one conversation. |
| PATCH | `/conversations/{conversation_id}` | Update conversation (e.g. title). |
| DELETE | `/conversations/{conversation_id}` | Delete conversation and its history. |

### POST /chat (main chat endpoint)

- **Body** (`ChatRequest`):
  ```json
  {
    "document_id": 1,
    "question": "What is the main topic of this document?",
    "conversation_id": null
  }
  ```
  - **conversation_id**: Omit or `null` to start a new conversation; send existing id to continue that thread.
- **Response**: `200` + `ChatResponse`:
  ```json
  {
    "answer": "The main topic is...",
    "source_documents": [
      { "content": "...", "metadata": {} }
    ],
    "conversation_id": 1
  }
  ```
- **Rate limit**: Per-user daily limit (`chat_limit`). When exceeded: `429 Too Many Requests`.
- **Behavior**: If the document has `sqlite_path` (structured), the **orchestrator** chooses SQL or RAG; otherwise **RAG only**. See [Document & Chat Behavior](#document--chat-behavior).

**UI flow**:  
1. User picks a document.  
2. Optionally create a conversation first via **POST /chat/conversations** (or let first **POST /chat** create it).  
3. **POST /chat** with `document_id`, `question`, and `conversation_id` (if continuing).  
4. Store `conversation_id` from response for follow-up messages.  
5. Use **GET /chat/history?conversation_id=...** to show the thread.

### GET /chat/history

- **Query**: `document_id` (optional), `conversation_id` (optional).
- **Response**: `200` + array of `ChatHistoryResponse` (id, conversation_id, document_id, question, answer, prompt_tokens, completion_tokens, created_at).

### GET /chat/history/{chat_id}

- **Response**: `200` + single `ChatHistoryResponse`.

### POST /chat/conversations

- **Body**:
  ```json
  {
    "document_id": 1,
    "title": "Discussion about policies"
  }
  ```
  - `title` optional; can be auto-generated from first question.
- **Response**: `201` + `ConversationResponse` (id, user_id, document_id, title, created_at, updated_at).

### GET /chat/conversations

- **Query**: `document_id` (optional).
- **Response**: `200` + array of `ConversationResponse` (e.g. for sidebar per document).

### GET /chat/conversations/{conversation_id}

- **Response**: `200` + `ConversationResponse`.

### PATCH /chat/conversations/{conversation_id}

- **Body**: `{ "title": "New title" }`
- **Response**: `200` + `ConversationResponse`.

### DELETE /chat/conversations/{conversation_id}

- **Response**: `204 No Content`. Removes conversation and all its chat history.

---

## Statistics API

**Prefix**: `/api/v1/statistics`

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET | `/user` | Authenticated | Current user stats. |
| GET | `/organization/{organization_id}` | Org access / Admin / SuperAdmin | Organization stats. |
| GET | `/admin` | Admin, SuperAdmin | System-wide admin stats. |

### GET /statistics/user

- **Response**: `200` + `UserStatistics`:
  - `total_documents`, `total_conversations`, `total_chats`, `total_tokens_used`
  - `chats_today`, `chats_remaining_today`, `chat_limit`
  - `documents_by_category` (map category → count)
  - `recent_activity` (list of activity objects)

### GET /statistics/organization/{organization_id}

- **Response**: `200` + `OrganizationStatistics`:
  - `organization_id`, `organization_name`, `total_users`, `total_documents`, `total_conversations`, `total_chats`, `total_tokens_used`, `active_users`
  - `documents_by_category`, `users_by_role`
  - `recent_activity`

### GET /statistics/admin

- **Response**: `200` + `AdminStatistics`:
  - Totals (organizations, users, documents, conversations, chats, tokens), `active_organizations`, `active_users`
  - `users_by_role`, `documents_by_category`
  - `organizations_stats` (array of org-level stats), `recent_activity`

---

## Admin API

**Prefix**: `/api/v1/admin`

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET | `/superadmins` | SuperAdmin | List superadmins. |
| POST | `/superadmins` | SuperAdmin | Create superadmin. |
| GET | `/admins` | Admin, SuperAdmin | List admins. |
| POST | `/admins` | SuperAdmin | Create admin. |

### GET /admin/superadmins

- **Query**: `skip`, `limit`.
- **Response**: `200` + array of `UserResponse`.

### POST /admin/superadmins

- **Body**: Same as user create; role forced to SUPER_ADMIN, no organization.
- **Response**: `201` + `UserResponse`.

### GET /admin/admins

- **Query**: `skip`, `limit`.
- **Response**: `200` + array of `UserResponse`.

### POST /admin/admins

- **Body**: Same as user create; role forced to ADMIN.
- **Response**: `201` + `UserResponse`.

---

## Roles & Access

| Role | Description | Documents / Chat | Orgs | Users |
|------|-------------|------------------|------|--------|
| **SUPER_ADMIN** | Full system access | All | All, delete | All, create SuperAdmin/Admin, delete any |
| **ADMIN** | System admin | All | All, CRUD (no delete org) | All, create org users / private users |
| **ORG_ADMIN** | Org admin | Own org: upload, chat, list | Own org only | Own org: list, create org_user |
| **ORG_USER** | Org member | Own org: upload, chat, list | Own org only | Self only |
| **USER** | Private user | No documents, no chat | None | Self only |

- **Private user** = role `USER`, `organization_id` null. Cannot use document or chat APIs.
- **Organization user** = ORG_ADMIN or ORG_USER; must have `organization_id` set.

---

## Error Responses

| Code | Meaning |
|------|--------|
| `200` | Success (GET/PATCH). |
| `201` | Created (POST). |
| `204` | No Content (DELETE). |
| `400` | Bad Request (validation, unsupported file type, etc.). |
| `401` | Unauthorized (missing or invalid token). |
| `403` | Forbidden (insufficient permissions). |
| `404` | Not Found (wrong id or no access). |
| `409` | Conflict (e.g. duplicate email/username). |
| `429` | Too Many Requests (chat limit exceeded). |
| `500` | Internal Server Error. |

Error body is typically: `{ "detail": "message" }` (string or list of validation errors).

---

## Document & Chat Behavior

### Document types

- **Unstructured** (PDF, DOCX, TXT, HTML, MD): Only vector store is created. Chat uses **RAG only** (retrieval + LLM).
- **Structured** (Excel, CSV, SQLite): Backend creates a SQLite DB and a vector store from row-level text. Stored paths:
  - `artifacts/{organization_id}/uploads/...`
  - `artifacts/{organization_id}/vector_store/...`
  - `artifacts/{organization_id}/structured_data/...` (SQLite).  
  Document record has `sqlite_path` set. Chat uses the **orchestrator**: each question is classified as **SQL** (aggregations, counts, etc.) or **RAG** (descriptive); then either the SQL agent or the RAG chain is used.

### Prompt building (organization users)

For org users, the system builds the AI prompt from (in order):

1. Organization description  
2. Category description (if document has a category and one is defined)  
3. Organization system prompt  

So the same document in different orgs (or categories) can get different context. Private users use only their own `system_prompt` (and cannot use documents/chat).

### UI implications

- Show document type (e.g. “PDF” vs “Excel/CSV/DB”) and optionally “Hybrid (SQL + RAG)” when `document.sqlite_path` is set.
- For chat: one **conversation** per document thread; **POST /chat** returns `conversation_id` to use for follow-up questions.
- Use **GET /statistics/user** to show “X of Y chats today” and remaining limit.

---

## Quick Reference: All Endpoints

| Method | Path |
|--------|------|
| POST | `/auth/signup` |
| POST | `/auth/login` |
| GET | `/auth/me` |
| POST | `/auth/refresh` |
| PATCH | `/auth/me/system-prompt` |
| POST | `/users` |
| GET | `/users` |
| GET | `/users/{user_id}` |
| PATCH | `/users/{user_id}` |
| DELETE | `/users/{user_id}` |
| PATCH | `/users/{user_id}/password` |
| PATCH | `/users/{user_id}/chat-limit` |
| PATCH | `/users/{user_id}/activate` |
| POST | `/organizations` |
| GET | `/organizations` |
| GET | `/organizations/{organization_id}` |
| PATCH | `/organizations/{organization_id}` |
| DELETE | `/organizations/{organization_id}` |
| GET | `/organizations/{organization_id}/users` |
| POST | `/organizations/{organization_id}/users` |
| POST | `/organizations/{organization_id}/categories` |
| GET | `/organizations/{organization_id}/categories` |
| GET | `/organizations/{organization_id}/categories/{category}` |
| PATCH | `/organizations/{organization_id}/categories/{category}` |
| DELETE | `/organizations/{organization_id}/categories/{category}` |
| POST | `/documents/upload` |
| GET | `/documents` |
| GET | `/documents/{document_id}` |
| DELETE | `/documents/{document_id}` |
| POST | `/chat` |
| GET | `/chat/history` |
| GET | `/chat/history/{chat_id}` |
| POST | `/chat/conversations` |
| GET | `/chat/conversations` |
| GET | `/chat/conversations/{conversation_id}` |
| PATCH | `/chat/conversations/{conversation_id}` |
| DELETE | `/chat/conversations/{conversation_id}` |
| GET | `/statistics/user` |
| GET | `/statistics/organization/{organization_id}` |
| GET | `/statistics/admin` |
| GET | `/admin/superadmins` |
| POST | `/admin/superadmins` |
| GET | `/admin/admins` |
| POST | `/admin/admins` |

All paths are relative to **`/api/v1`**.
