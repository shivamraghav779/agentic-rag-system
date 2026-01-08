# Multi-Tenancy Implementation Guide

## Overview

The system supports a hierarchical multi-tenancy structure with role-based access control:

```
SuperAdmin
  └── Admins
      └── Organizations
          ├── Organization Admins (ORG_ADMIN)
          └── Organization Users (ORG_USER)
```

**Note**: Sub-organizations have been removed. Users are now directly associated with organizations.

## Role Hierarchy

### 1. SuperAdmin (SUPER_ADMIN)
- **Access**: Full system access
- **Organization**: Not associated with any organization (`organization_id = null`)
- **Can**: 
  - Manage all organizations
  - Create/delete organizations
  - Create SuperAdmin and Admin users
  - Manage all users
  - Access all documents and chats
  - Delete any user

### 2. Admin (ADMIN)
- **Access**: Can manage organizations
- **Organization**: May or may not be associated with an organization
- **Can**:
  - Create/update/delete organizations
  - Manage users (except SuperAdmin and Admin)
  - Create ORG_ADMIN, ORG_USER, and USER (private) roles
  - Access all documents and chats
- **Cannot**:
  - Create/modify SuperAdmin or Admin users
  - Delete users

### 3. Organization Admin (ORG_ADMIN)
- **Access**: Manages a specific organization
- **Organization**: Must be associated with an organization (`organization_id` required)
- **Can**:
  - Manage users in their organization (can only create ORG_USER)
  - Upload/manage documents in their organization
  - Chat with documents in their organization
  - Access all documents in their organization
- **Cannot**:
  - Create ORG_ADMIN, ADMIN, or SUPER_ADMIN users
  - Access other organizations
  - Manage users outside their organization

### 4. Organization User (ORG_USER)
- **Access**: Regular user within an organization
- **Organization**: Must be associated with an organization (`organization_id` required)
- **Can**:
  - Upload/view documents in their organization
  - Chat with documents in their organization
  - View their own conversations and chat history
- **Cannot**:
  - Manage other users
  - Access other organizations
  - Manage documents (only upload and view)

### 5. Private User (USER)
- **Access**: Private user, not in any organization
- **Organization**: Not associated with any organization (`organization_id = null`)
- **Can**:
  - View and update their own profile
  - Update their system prompt
  - Sign up and login
- **Cannot**:
  - Upload documents
  - Chat with documents
  - Access any organization resources
  - Manage other users

## Database Schema

### Organizations Table
- `id`: Primary key
- `name`: Organization name (required, indexed)
- `description`: Optional description
- `is_active`: Active status (default: true)
- `created_at`, `updated_at`: Timestamps

### Users Table (Updated)
- `id`: Primary key
- `username`: Unique username (required, indexed)
- `email`: Unique email (required, indexed)
- `hashed_password`: Argon2 hashed password
- `is_active`: Active status (default: true)
- `role`: Enum (SUPER_ADMIN, ADMIN, ORG_ADMIN, ORG_USER, USER) - default: USER
- `organization_id`: Foreign key to organizations (nullable)
  - Required for ORG_ADMIN and ORG_USER
  - Must be null for USER (private) and SUPER_ADMIN
  - Optional for ADMIN
- `chat_limit`: Daily chat limit (default: 3)
- `system_prompt`: Custom system prompt for AI (nullable)
- `used_tokens`: Total tokens used (default: 0)
- `is_admin`: Legacy flag (deprecated, use role instead)
- `created_at`: Timestamp

### Documents Table (Updated)
- `id`: Primary key
- `user_id`: Foreign key to users (uploader)
- `organization_id`: Foreign key to organizations (required)
- `filename`: Original filename
- `file_type`: File type (pdf, docx, txt, html)
- `file_path`: Path to uploaded file
- `vector_store_path`: Path to FAISS vector store
- `upload_date`: Upload timestamp
- `file_size`: Size in bytes
- `chunk_count`: Number of text chunks
- `category`: String (VARCHAR(100)) - Organization-specific category name (e.g., "HR", "Sales", "Legal", "Operations", "General")
- `version`: Version number (default: 1)
- `extra_metadata`: JSON string for additional metadata

### Conversations Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `document_id`: Foreign key to documents
- `title`: Conversation title (auto-generated from first question)
- `created_at`, `updated_at`: Timestamps

### ChatHistory Table
- `id`: Primary key
- `conversation_id`: Foreign key to conversations
- `user_id`: Foreign key to users
- `document_id`: Foreign key to documents
- `question`: User's question
- `answer`: AI's response
- `prompt_tokens`: Tokens used in prompt
- `completion_tokens`: Tokens used in completion
- `created_at`: Timestamp

## Access Control Logic

### User.can_access_organization(org_id)
```python
- SUPER_ADMIN: Always True
- ADMIN: Always True
- ORG_ADMIN: True if organization_id == org_id
- ORG_USER: True if organization_id == org_id
- USER (private): Always False
```

### User.is_organization_user()
```python
- Returns True if role is ORG_ADMIN or ORG_USER and organization_id is not None
```

### User.is_private_user()
```python
- Returns True if role is USER and organization_id is None
```

## API Endpoints

### Organization Management

#### Create Organization
```
POST /api/v1/organizations
```
- **Access**: SuperAdmin, Admin
- **Body**: `OrganizationCreate` (includes `admin_user` credentials)
- **Returns**: `OrganizationResponse`
- **Notes**: Automatically creates an ORG_ADMIN user for the organization

#### List Organizations
```
GET /api/v1/organizations?skip=0&limit=100
```
- **Access**: All authenticated users (filtered by role)
- **Returns**: `List[OrganizationResponse]`
- **Access Control**:
  - SuperAdmin/Admin: See all organizations
  - OrgAdmin/OrgUser: See only their organization
  - Private User: See no organizations

#### Get Organization
```
GET /api/v1/organizations/{organization_id}
```
- **Access**: Users with access to the organization
- **Returns**: `OrganizationResponse`

#### Update Organization
```
PATCH /api/v1/organizations/{organization_id}
```
- **Access**: SuperAdmin, Admin
- **Body**: `OrganizationUpdate`
- **Returns**: `OrganizationResponse`

#### Delete Organization
```
DELETE /api/v1/organizations/{organization_id}
```
- **Access**: SuperAdmin only
- **Returns**: 204 No Content

### Organization User Management

#### List Organization Users
```
GET /api/v1/organizations/{organization_id}/users?role=org_user&skip=0&limit=100
```
- **Access**: Users with access to the organization
- **Query Parameters**:
  - `role` (optional): Filter by role (ORG_ADMIN, ORG_USER)
  - `skip`, `limit`: Pagination
- **Returns**: `List[UserResponse]`

#### Create Organization User
```
POST /api/v1/organizations/{organization_id}/users
```
- **Access**: OrgAdmin, Admin, SuperAdmin
- **Body**: `UserCreate` (organization_id will be set automatically)
- **Returns**: `UserResponse`
- **Notes**: 
  - OrgAdmins can only create ORG_USER role
  - Only ORG_ADMIN and ORG_USER roles can be created in organizations

### Document Management

#### Upload Document
```
POST /api/v1/documents/upload?organization_id=1&category=HR
```
- **Access**: Organization users (ORG_ADMIN, ORG_USER)
- **Parameters**:
  - `organization_id` (optional): Defaults to user's organization
  - `category` (optional): Document category (organization-specific string, e.g., "HR", "Sales", "Legal")
- **Body**: File upload (PDF, DOCX, TXT, HTML)
- **Returns**: `UploadResponse`
- **Notes**: Private users cannot upload documents

#### List Documents
```
GET /api/v1/documents?organization_id=1&category=HR
```
- **Access**: Organization users (filtered by organization access)
- **Parameters**:
  - `organization_id` (optional): Filter by organization
  - `category` (optional): Filter by category
- **Returns**: `List[DocumentInfo]`
- **Notes**: Private users cannot access documents

#### Get Document
```
GET /api/v1/documents/{document_id}
```
- **Access**: Organization users with access to the document's organization
- **Returns**: `DocumentInfo`

#### Delete Document
```
DELETE /api/v1/documents/{document_id}
```
- **Access**: 
  - Document owner
  - OrgAdmin (for documents in their org)
  - Admin, SuperAdmin
- **Returns**: 204 No Content
- **Notes**: Private users cannot delete documents

#### Category Management

Organizations can define custom document categories with descriptions. Categories are organization-specific strings (not enums), allowing flexibility.

##### Create Category Description
```
POST /api/v1/organizations/{organization_id}/categories
```
- **Access**: SuperAdmin, Admin, OrgAdmin (for their organization)
- **Body**: 
  ```json
  {
    "category": "HR",
    "description": "Human Resources documents including policies, procedures, and employee handbooks."
  }
  ```
- **Returns**: `DocumentCategoryDescriptionResponse`
- **Notes**: Category names are organization-specific (e.g., "HR", "Sales", "Legal", "Operations")

##### List Category Descriptions
```
GET /api/v1/organizations/{organization_id}/categories
```
- **Access**: Users with access to the organization
- **Returns**: `List[DocumentCategoryDescriptionResponse]`

##### Update Category Description
```
PATCH /api/v1/organizations/{organization_id}/categories/{category}
```
- **Access**: SuperAdmin, Admin, OrgAdmin (for their organization)
- **Body**: 
  ```json
  {
    "description": "Updated description"
  }
  ```
- **Returns**: `DocumentCategoryDescriptionResponse`
- **Notes**: Only description can be updated, category name cannot be changed

##### Delete Category Description
```
DELETE /api/v1/organizations/{organization_id}/categories/{category}
```
- **Access**: SuperAdmin, Admin, OrgAdmin (for their organization)
- **Returns**: 204 No Content
- **Notes**: Deleting a category description does not delete documents with that category

### Chat Management

All chat endpoints verify organization access before allowing document queries.

#### Chat with Document
```
POST /api/v1/chat
```
- **Access**: Organization users (ORG_ADMIN, ORG_USER)
- **Body**: `ChatRequest` (document_id, question, optional conversation_id)
- **Returns**: `ChatResponse` (answer, source_documents, conversation_id)
- **Notes**: 
  - Rate limited based on user's `chat_limit` (per day)
  - Private users cannot chat with documents

#### Get Chat History
```
GET /api/v1/chat/history?document_id=1&conversation_id=1
```
- **Access**: Organization users
- **Returns**: `List[ChatHistoryResponse]`
- **Notes**: Private users cannot access chat history

## Prompt System

The system uses a hierarchical prompt building system for AI responses:

### Private Users
- Use their personal `system_prompt` (set via `/api/v1/auth/me/system-prompt`)
- Each private user can customize their own system prompt

### Organization Users
The prompt is built from multiple sources, combined in this order:
1. **Organization Description**: Context about the organization (from `organizations.description`)
2. **Category Description**: Description of the document's category (if document has a category and category description exists)
3. **Organization System Prompt**: Common system prompt for all organization users (from `organizations.system_prompt`)

This allows for:
- **Organization-specific context**: All users in an organization get the same organizational context
- **Category-specific guidance**: Documents in different categories can have specialized instructions
- **Consistent behavior**: All organization users share the same system prompt, ensuring consistent AI behavior
- **Flexibility**: Organizations can customize prompts without affecting individual users

**Example Prompt Structure for Organization Users:**
```
Organization Context:
[Organization description]

Knowledge Base Category (HR):
[Category description if exists]

System Instructions:
[Organization system prompt]
```

## Migration Notes

### Key Migrations

1. **`31eb3f74e5a3_add_multi_tenancy_models.py`**:
   - Creates `organizations` table
   - Adds `role`, `organization_id` to `users` table
   - Adds `organization_id`, `category` (VARCHAR), `version` to `documents` table
   - Creates `document_category_descriptions` table for organization-specific category descriptions
   - Adds `system_prompt` to `organizations` table
   - Creates a default organization for existing data
   - Sets default roles for existing users

2. **`0f5d49da2193_remove_sub_organizations.py`**:
   - Removes `sub_organizations` table
   - Removes `sub_organization_id` from `users` and `documents` tables
   - Updates existing SUB_ORG_ADMIN users to USER role

3. **`15f4e7f7e618_add_org_user_role_and_separate_private_users.py`**:
   - Adds `ORG_USER` role to enum
   - Updates existing USER role users with `organization_id` to `ORG_USER`
   - Sets `organization_id` to null for private USER role users

4. **`8d9e2efd309c_add_category_descriptions_and_system_prompt.py`**:
   - Adds `system_prompt` column to `organizations` table
   - Creates `document_category_descriptions` table for organization-specific category descriptions
   - Converts `documents.category` from ENUM to VARCHAR(100) for flexibility
   - Allows organizations to define custom category names

## Usage Examples

### Creating a SuperAdmin User
```python
from app.models.user import User, UserRole
from app.core.security import get_password_hash

super_admin = User(
    username="superadmin",
    email="superadmin@example.com",
    hashed_password=get_password_hash("password"),
    role=UserRole.SUPER_ADMIN,
    organization_id=None,  # SuperAdmin not in organization
    is_active=True,
    chat_limit=1000
)
```

### Creating an Organization
```bash
curl -X POST "http://localhost:8000/api/v1/organizations" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "description": "Main organization",
    "is_active": true,
    "admin_user": {
      "username": "org_admin",
      "email": "admin@acme.com",
      "password": "secure_password123"
    }
  }'
```

This automatically creates an ORG_ADMIN user for the organization.

### Creating an Organization User
```bash
curl -X POST "http://localhost:8000/api/v1/organizations/1/users" \
  -H "Authorization: Bearer <org_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "employee1",
    "email": "employee1@acme.com",
    "password": "password",
    "role": "org_user",
    "chat_limit": 10
  }'
```

### Uploading a Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload?category=HR" \
  -H "Authorization: Bearer <org_user_token>" \
  -F "file=@document.pdf"
```

### Chatting with a Document
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer <org_user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "question": "What is the main topic of this document?"
  }'
```

## Important Notes

1. **Private Users (USER role)**:
   - Cannot upload documents
   - Cannot chat with documents
   - Cannot access any organization resources
   - Are completely separate from organization users

2. **Organization Users (ORG_ADMIN, ORG_USER)**:
   - Must have an `organization_id`
   - Can upload and chat with documents
   - Are scoped to their organization

3. **Role Assignment Rules**:
   - ORG_ADMIN and ORG_USER: Must have `organization_id`
   - USER (private): Must have `organization_id = null`
   - SUPER_ADMIN: Should have `organization_id = null`
   - ADMIN: `organization_id` is optional

4. **Access Control**:
   - All document and chat operations verify organization access
   - Private users are explicitly blocked from organization-scoped operations
   - Organization users can only access resources in their organization

## Next Steps

1. **Analytics**: Organization-level usage analytics
2. **Document Sharing**: Cross-organization document sharing (if needed)
3. **Permissions**: Fine-grained permissions system within organizations
4. **Bulk Operations**: Bulk document upload/management
5. **Organization Settings**: Customizable organization-level settings
