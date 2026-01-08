# Comprehensive CRUD API Documentation

## Overview

This document describes all CRUD operations available for users, organizations, sub-organizations, admins, and superadmins in the multi-tenant system.

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
    "role": "user",
    "organization_id": 1,
    "sub_organization_id": 2,
    "chat_limit": 10
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - Admins cannot create SuperAdmin or Admin users
  - Organization and sub-organization must be valid

### List Users
```
GET /api/v1/users?organization_id=1&sub_organization_id=2&role=user&skip=0&limit=100
```
- **Access**: All authenticated users (filtered by role)
- **Query Parameters**:
  - `organization_id` (optional): Filter by organization
  - `sub_organization_id` (optional): Filter by sub-organization
  - `role` (optional): Filter by role (SUPER_ADMIN, ADMIN, ORG_ADMIN, SUB_ORG_ADMIN, USER)
  - `skip` (default: 0): Pagination offset
  - `limit` (default: 100, max: 100): Pagination limit
- **Returns**: `List[UserResponse]`
- **Access Control**:
  - SuperAdmin/Admin: See all users
  - OrgAdmin: See users in their organization
  - SubOrgAdmin: See users in their sub-organization
  - User: See only themselves

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
    "sub_organization_id": 2,
    "chat_limit": 20,
    "is_active": true,
    "system_prompt": "Custom prompt"
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - Admins cannot modify SuperAdmin or Admin users
  - Changing organization clears sub-organization if not specified

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
    "slug": "acme-corp",
    "description": "Main organization",
    "is_active": true
  }
  ```
- **Returns**: `OrganizationResponse`

### List Organizations
```
GET /api/v1/organizations?skip=0&limit=100
```
- **Access**: All authenticated users (filtered by role)
- **Returns**: `List[OrganizationResponse]`

### Get Organization
```
GET /api/v1/organizations/{organization_id}
```
- **Access**: Users with access to the organization
- **Returns**: `OrganizationWithSubOrgs` (includes sub-organizations)

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
GET /api/v1/organizations/{organization_id}/users?role=user&skip=0&limit=100
```
- **Access**: Users with access to the organization
- **Query Parameters**:
  - `role` (optional): Filter by role
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
    "role": "user",
    "sub_organization_id": 2,
    "chat_limit": 5
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - OrgAdmins can only create USER and SUB_ORG_ADMIN roles
  - Organization ID is automatically set

## Sub-Organization Management (`/api/v1/organizations/{organization_id}/sub-organizations`)

### Create Sub-Organization
```
POST /api/v1/organizations/{organization_id}/sub-organizations
```
- **Access**: OrgAdmin, Admin, SuperAdmin
- **Body**: `SubOrganizationCreate`
  ```json
  {
    "name": "Sales Department",
    "description": "Sales team",
    "is_active": true,
    "admin_user": {
      "username": "sales_admin",
      "email": "sales_admin@acme.com",
      "password": "secure_password123"
    }
  }
  ```
- **Returns**: `SubOrganizationResponse`
- **Notes**: 
  - Automatically creates a SUB_ORG_ADMIN user for the sub-organization
  - Admin user is assigned to the organization and sub-organization
  - Admin user gets default chat_limit of 50

### List Sub-Organizations
```
GET /api/v1/organizations/{organization_id}/sub-organizations
```
- **Access**: Users with access to the organization
- **Returns**: `List[SubOrganizationResponse]`

### Get Sub-Organization
```
GET /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}
```
- **Access**: Users with access to the sub-organization
- **Returns**: `SubOrganizationResponse`

### Update Sub-Organization
```
PATCH /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}
```
- **Access**: OrgAdmin, Admin, SuperAdmin
- **Body**: `SubOrganizationUpdate`
  ```json
  {
    "name": "Updated Name",
    "description": "Updated description",
    "is_active": false
  }
  ```
- **Returns**: `SubOrganizationResponse`

### Delete Sub-Organization
```
DELETE /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}
```
- **Access**: OrgAdmin, Admin, SuperAdmin
- **Returns**: 204 No Content

## Sub-Organization User Management (`/api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}/users`)

### List Sub-Organization Users
```
GET /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}/users?role=user&skip=0&limit=100
```
- **Access**: Users with access to the sub-organization
- **Query Parameters**:
  - `role` (optional): Filter by role
  - `skip`, `limit`: Pagination
- **Returns**: `List[UserResponse]`

### Create Sub-Organization User
```
POST /api/v1/organizations/{organization_id}/sub-organizations/{sub_org_id}/users
```
- **Access**: SubOrgAdmin, OrgAdmin, Admin, SuperAdmin
- **Body**: `UserCreate` (organization_id and sub_organization_id will be set automatically)
  ```json
  {
    "username": "suborg_user",
    "email": "suborg_user@example.com",
    "password": "password",
    "role": "user",
    "chat_limit": 5
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: 
  - SubOrgAdmins can only create USER role
  - Organization and sub-organization IDs are automatically set

## Admin Management API (`/api/v1/admin`)

### List All Users (Admin)
```
GET /api/v1/admin/users?role=admin&organization_id=1&skip=0&limit=100
```
- **Access**: Admin, SuperAdmin
- **Query Parameters**: Same as `/api/v1/users`
- **Returns**: `List[UserResponse]`
- **Note**: Legacy endpoint, use `/api/v1/users` for comprehensive filtering

### Get User (Admin)
```
GET /api/v1/admin/users/{user_id}
```
- **Access**: Admin, SuperAdmin
- **Returns**: `UserResponse`

### Update User Chat Limit (Admin)
```
PATCH /api/v1/admin/users/{user_id}/chat-limit
```
- **Access**: Admin, SuperAdmin
- **Body**: `ChatLimitUpdate`
- **Returns**: `UserResponse`

### Toggle User Active Status (Admin)
```
PATCH /api/v1/admin/users/{user_id}/activate
```
- **Access**: Admin, SuperAdmin
- **Returns**: `UserResponse`
- **Notes**: 
  - Cannot deactivate your own account
  - Admins cannot deactivate SuperAdmin or Admin users

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
  - Organization and sub-organization are set to null

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
    "organization_id": 1,
    "chat_limit": 500
  }
  ```
- **Returns**: `UserResponse`
- **Notes**: Role is automatically set to ADMIN

## Role-Based Access Summary

### SuperAdmin
- ✅ Full CRUD on all entities
- ✅ Can create SuperAdmin and Admin users
- ✅ Can delete any user
- ✅ Can manage all organizations

### Admin
- ✅ Can create ORG_ADMIN, SUB_ORG_ADMIN, USER
- ❌ Cannot create/modify SuperAdmin or Admin users
- ✅ Can manage organizations
- ✅ Can see all users

### OrgAdmin
- ✅ Can create SUB_ORG_ADMIN, USER in their organization
- ✅ Can manage sub-organizations in their organization
- ✅ Can see users in their organization
- ❌ Cannot create ORG_ADMIN, ADMIN, SUPER_ADMIN

### SubOrgAdmin
- ✅ Can create USER in their sub-organization
- ✅ Can see users in their sub-organization
- ❌ Cannot create any admin roles

### User
- ✅ Can see only themselves
- ✅ Can access documents in their organization
- ❌ Cannot manage other users

## Example Workflows

### Creating a Complete Organization Structure

1. **Create Organization** (SuperAdmin/Admin):
   ```bash
   POST /api/v1/organizations
   {
     "name": "Tech Corp",
     "slug": "tech-corp",
     "is_active": true
   }
   ```

2. **Create Organization Admin** (SuperAdmin/Admin):
   ```bash
   POST /api/v1/organizations/1/users
   {
     "username": "org_admin",
     "email": "org_admin@techcorp.com",
     "password": "password",
     "role": "org_admin",
     "chat_limit": 100
   }
   ```

3. **Create Sub-Organization** (OrgAdmin/Admin/SuperAdmin):
   ```bash
   POST /api/v1/organizations/1/sub-organizations
   {
     "name": "Engineering",
     "slug": "engineering",
     "is_active": true
   }
   ```

4. **Create Sub-Organization Admin** (OrgAdmin/Admin/SuperAdmin):
   ```bash
   POST /api/v1/organizations/1/sub-organizations/1/users
   {
     "username": "suborg_admin",
     "email": "suborg_admin@techcorp.com",
     "password": "password",
     "role": "sub_org_admin",
     "chat_limit": 50
   }
   ```

5. **Create Regular Users** (SubOrgAdmin/OrgAdmin/Admin/SuperAdmin):
   ```bash
   POST /api/v1/organizations/1/sub-organizations/1/users
   {
     "username": "engineer1",
     "email": "engineer1@techcorp.com",
     "password": "password",
     "role": "user",
     "chat_limit": 10
   }
   ```

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

