# Multi-Tenancy Implementation Guide

## Overview

The system now supports a hierarchical multi-tenancy structure:

```
SuperAdmin
  └── Admins
      └── Organizations
          ├── Organization Admins
          └── SubOrganizations
              ├── SubOrgAdmins
              └── Users
```

## Role Hierarchy

### 1. SuperAdmin
- **Access**: Full system access
- **Can**: 
  - Manage all organizations
  - Create/delete organizations
  - Manage all users
  - Access all documents

### 2. Admin
- **Access**: Can manage organizations
- **Can**:
  - Create/update/delete organizations
  - Manage users within organizations
  - Access all documents

### 3. Organization Admin (ORG_ADMIN)
- **Access**: Manages a specific organization
- **Can**:
  - Manage sub-organizations within their organization
  - Manage users in their organization
  - Upload/manage documents in their organization
  - Access all documents in their organization

### 4. Sub-Organization Admin (SUB_ORG_ADMIN)
- **Access**: Manages a specific sub-organization
- **Can**:
  - Manage users in their sub-organization
  - Upload/manage documents in their sub-organization
  - Access documents in their sub-organization

### 5. User
- **Access**: Regular user
- **Can**:
  - Access documents in their organization
  - Chat with documents in their organization
  - View their own conversations

## Database Schema

### Organizations Table
- `id`: Primary key
- `name`: Organization name
- `slug`: URL-friendly identifier (unique)
- `description`: Optional description
- `is_active`: Active status
- `created_at`, `updated_at`: Timestamps

### Sub-Organizations Table
- `id`: Primary key
- `organization_id`: Foreign key to organizations
- `name`: Sub-organization name
- `slug`: URL-friendly identifier (unique within organization)
- `description`: Optional description
- `is_active`: Active status
- `created_at`, `updated_at`: Timestamps

### Users Table (Updated)
- `role`: Enum (SUPER_ADMIN, ADMIN, ORG_ADMIN, SUB_ORG_ADMIN, USER)
- `organization_id`: Foreign key to organizations (nullable)
- `sub_organization_id`: Foreign key to sub_organizations (nullable)

### Documents Table (Updated)
- `organization_id`: Foreign key to organizations (required)
- `sub_organization_id`: Foreign key to sub_organizations (optional)
- `category`: Enum (HR, SALES, LEGAL, OPS, GENERAL)
- `version`: Integer for version control

## API Endpoints

### Organization Management

#### Create Organization
```
POST /api/v1/organizations
```
- **Access**: SuperAdmin, Admin
- **Body**: `OrganizationCreate`
- **Returns**: `OrganizationResponse`

#### List Organizations
```
GET /api/v1/organizations?skip=0&limit=100
```
- **Access**: All authenticated users (filtered by role)
- **Returns**: `List[OrganizationResponse]`

#### Get Organization
```
GET /api/v1/organizations/{organization_id}
```
- **Access**: Users with access to the organization
- **Returns**: `OrganizationWithSubOrgs`

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

### Sub-Organization Management

#### Create Sub-Organization
```
POST /api/v1/organizations/{organization_id}/sub-organizations
```
- **Access**: Organization Admin, Admin, SuperAdmin
- **Body**: `SubOrganizationCreate`
- **Returns**: `SubOrganizationResponse`

#### List Sub-Organizations
```
GET /api/v1/organizations/{organization_id}/sub-organizations
```
- **Access**: Users with access to the organization
- **Returns**: `List[SubOrganizationResponse]`

#### Get Sub-Organization
```
GET /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}
```
- **Access**: Users with access to the sub-organization
- **Returns**: `SubOrganizationResponse`

#### Update Sub-Organization
```
PATCH /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}
```
- **Access**: Organization Admin, Admin, SuperAdmin
- **Body**: `SubOrganizationUpdate`
- **Returns**: `SubOrganizationResponse`

#### Delete Sub-Organization
```
DELETE /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}
```
- **Access**: Organization Admin, Admin, SuperAdmin
- **Returns**: 204 No Content

### Document Management (Updated)

#### Upload Document
```
POST /api/v1/documents/upload?organization_id=1&sub_organization_id=2&category=HR
```
- **Access**: Users with access to the organization
- **Parameters**:
  - `organization_id` (optional): Defaults to user's organization
  - `sub_organization_id` (optional): For sub-org scoped documents
  - `category` (optional): Document category (default: GENERAL)
- **Body**: File upload
- **Returns**: `UploadResponse`

#### List Documents
```
GET /api/v1/documents?organization_id=1&sub_organization_id=2&category=HR
```
- **Access**: Users (filtered by organization access)
- **Parameters**:
  - `organization_id` (optional): Filter by organization
  - `sub_organization_id` (optional): Filter by sub-organization
  - `category` (optional): Filter by category
- **Returns**: `List[DocumentInfo]`

#### Get Document
```
GET /api/v1/documents/{document_id}
```
- **Access**: Users with access to the document's organization
- **Returns**: `DocumentInfo`

#### Delete Document
```
DELETE /api/v1/documents/{document_id}
```
- **Access**: 
  - Document owner
  - Organization Admin (for documents in their org)
  - Sub-Org Admin (for documents in their sub-org)
  - Admin, SuperAdmin
- **Returns**: 204 No Content

### Chat (Updated)

All chat endpoints now verify organization access before allowing document queries.

## Access Control Logic

### User.can_access_organization(org_id)
- SuperAdmin: Always true
- Admin: Always true
- OrgAdmin: True if `organization_id == org_id`
- Others: False

### User.can_access_sub_organization(sub_org_id)
- SuperAdmin: Always true
- Admin: Always true
- OrgAdmin: True (checked in service layer with DB query)
- SubOrgAdmin: True if `sub_organization_id == sub_org_id`
- Others: False

## Migration Notes

The migration `31eb3f74e5a3_add_multi_tenancy_models.py`:
1. Creates `organizations` and `sub_organizations` tables
2. Adds `role`, `organization_id`, `sub_organization_id` to `users` table
3. Adds `organization_id`, `sub_organization_id`, `category`, `version` to `documents` table
4. Creates a default organization for existing data
5. Sets default roles for existing users based on `is_admin` flag
6. Assigns existing users to the default organization

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
    is_active=True
)
```

### Creating an Organization
```bash
curl -X POST "http://localhost:8000/api/v1/organizations" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "description": "Main organization",
    "is_active": true
  }'
```

### Creating a Sub-Organization
```bash
curl -X POST "http://localhost:8000/api/v1/organizations/1/sub-organizations" \
  -H "Authorization: Bearer <org_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Department",
    "slug": "sales",
    "description": "Sales team sub-organization",
    "is_active": true
  }'
```

### Uploading a Document to an Organization
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload?organization_id=1&category=HR" \
  -H "Authorization: Bearer <user_token>" \
  -F "file=@document.pdf"
```

## Next Steps

1. **User Management APIs**: Create endpoints for managing users within organizations
2. **Bulk Operations**: Add bulk document upload/management
3. **Analytics**: Organization-level usage analytics
4. **Document Sharing**: Cross-organization document sharing (if needed)
5. **Permissions**: Fine-grained permissions system

