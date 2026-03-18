# Role-Based Dashboard Pointers (UI Reference)

Short reference for each role: **description**, **actions the role can perform**, and **actions that can be performed on the role** by others. Use this to build role-specific dashboards and hide/show UI.

---

## 1. SUPER_ADMIN

**Description**  
Top-level system owner. No organization. Full access to all resources and all roles.

**Actions this role CAN do**
- **Auth**: Login, refresh, update own system prompt (rare; usually not org-bound).
- **Users**: List all users, create SuperAdmin/Admin/OrgAdmin/OrgUser/Private User, get/update/delete any user, change password/chat-limit/activate for any user.
- **Organizations**: Create, list all, get, update, **delete** any organization (and its artifacts).
- **Org users**: List/create users in any org (via `/organizations/{id}/users`).
- **Categories**: Create/list/get/update/delete category descriptions for any org.
- **Documents**: List/upload/get/delete documents in any org (via org access).
- **Chat**: Full chat and conversation access for any org document.
- **Statistics**: User stats, any org stats, **admin (system-wide) stats**.
- **Admin API**: List/create SuperAdmins, list/create Admins.

**Actions that can be performed ON this role**
- **Updated** by another SuperAdmin (username, email, chat_limit, is_active; not role).
- **Deleted** only by another SuperAdmin (cannot delete self).
- **Password / chat-limit / activate** only by another SuperAdmin.

**UI dashboard pointers**
- Show **Admin dashboard**: system stats, all orgs, all users, create SuperAdmin/Admin.
- Show **Organization selector** (all orgs); then org-level docs, chat, users, categories.
- Enable **Delete organization** only for SuperAdmin.
- Enable **Delete any user** and **Create SuperAdmin/Admin**.

---

## 2. ADMIN

**Description**  
System administrator under SuperAdmin. No organization. Manages organizations and users (cannot create/change SuperAdmin or Admin, cannot delete organizations).

**Actions this role CAN do**
- **Auth**: Login, refresh, update own system prompt.
- **Users**: List all users, create **OrgAdmin / OrgUser / Private User only**, get/update (but not delete) users; change password/chat-limit/activate for non–SuperAdmin/Admin users.
- **Organizations**: Create, list all, get, **update** (no delete).
- **Org users**: List/create users in any org.
- **Categories**: Full category CRUD for any org.
- **Documents**: List/upload/get/delete in any org.
- **Chat**: Full chat/conversations for any org document.
- **Statistics**: User stats, any org stats, **admin (system-wide) stats**.
- **Admin API**: **List** SuperAdmins and Admins only (no create SuperAdmin/Admin).

**Actions that can be performed ON this role**
- **Created** only by SuperAdmin.
- **Updated / password / chat-limit / activate** by SuperAdmin only (Admins cannot modify other Admins or SuperAdmins).
- **Deleted** only by SuperAdmin.

**UI dashboard pointers**
- Same as SuperAdmin **except**: hide **Delete organization**, hide **Delete user** and **Create SuperAdmin/Admin**.
- Show **Admin dashboard** with system and org stats; allow org CRUD except delete.

---

## 3. ORG_ADMIN

**Description**  
Administrator of a single organization. Manages that org’s users and content. Belongs to one organization (`organization_id` set).

**Actions this role CAN do**
- **Auth**: Login, refresh, update own system prompt.
- **Users**: List **only users in their org**; create **OrgUser only** in their org (via `/organizations/{id}/users`). Get/update users in their org (service rules apply).
- **Organizations**: List/get **only their organization** (no create/update/delete).
- **Org users**: List users in their org; create OrgUser in their org.
- **Categories**: Create/list/get/update/delete category descriptions **for their org only**.
- **Documents**: Upload, list, get, delete documents **in their org** (and own org’s categories).
- **Chat**: Full chat and conversations for **their org’s documents**.
- **Statistics**: Own **user stats**; **organization stats for their org only**.

**Actions that can be performed ON this role**
- **Created** by SuperAdmin, Admin, or OrgAdmin (same org, via create org user).
- **Updated / password / chat-limit / activate** by **SuperAdmin or Admin only** (central user API).
- **Deleted** by **SuperAdmin only**.

**UI dashboard pointers**
- **Single-org context**: no org selector; show current org name and org-level stats.
- **Org dashboard**: org stats, list of org users, add OrgUser, manage categories, list/upload/delete docs, chat.
- Hide: create/delete organization, create SuperAdmin/Admin, admin stats, other orgs’ data.
- Show **“Members”** (org users) and **“Add member”** (OrgUser only).

---

## 4. ORG_USER

**Description**  
Regular member of one organization. Can use documents and chat in that org; cannot manage users or org settings. Belongs to one organization.

**Actions this role CAN do**
- **Auth**: Login, refresh, update own system prompt.
- **Users**: List **only themselves** (get own profile).
- **Organizations**: List/get **only their organization**.
- **Org users**: No create; list org users (if endpoint returns org-scoped list; effectively may see only self depending on implementation).
- **Categories**: List/get category descriptions for their org (no create/update/delete).
- **Documents**: Upload, list, get, delete **own** or org documents (per document access rules: same org).
- **Chat**: Chat and conversations for **their org’s documents** (subject to daily chat limit).
- **Statistics**: Own **user stats** (documents, chats, limit remaining); **organization stats for their org**.

**Actions that can be performed ON this role**
- **Created** by SuperAdmin, Admin, or OrgAdmin (same org, via create org user).
- **Updated / password / chat-limit / activate** by **SuperAdmin or Admin only** (central user API).
- **Deleted** by **SuperAdmin only**.

**UI dashboard pointers**
- **Personal + org context**: “My stats” (docs, chats, limit), “My organization,” list of docs (org), chat with docs.
- Hide: user management, create/update/delete categories, create/delete org, admin stats, other orgs.
- Show **chat limit** (e.g. “X of Y chats today”) and **conversations** per document.
- **Upload** and **delete** only for docs they’re allowed to (org-scoped).

---

## 5. USER (Private user)

**Description**  
Private user with no organization. Can only use auth and their own profile; no documents, no chat, no org access.

**Actions this role CAN do**
- **Auth**: Signup (creates this role), login, refresh, **update own system prompt**.
- **Users**: List/get **only themselves**.
- **Organizations**: **None** (cannot list or access any org).
- **Categories**: None.
- **Documents**: **None** (no upload, list, get, delete).
- **Chat**: **None** (no chat, no conversations, no history).
- **Statistics**: **User stats only** (will show zeros for docs/chats if no org).

**Actions that can be performed ON this role**
- **Created** via signup (self) or by SuperAdmin/Admin (create user with role `USER`, `organization_id` null).
- **Updated / password / chat-limit / activate** by **SuperAdmin or Admin only**.
- **Deleted** by **SuperAdmin only**.

**UI dashboard pointers**
- **Minimal dashboard**: profile (username, email, system prompt), “Upgrade” or “Join organization” message.
- Hide: documents, chat, conversations, org list, categories, org stats, admin stats, any user/org management.
- Show **Edit profile** and **System prompt** only.

---

## Quick matrix (who can do what)

| Action                     | SuperAdmin | Admin | OrgAdmin | OrgUser | User |
|----------------------------|------------|-------|----------|---------|------|
| Create SuperAdmin/Admin    | ✓          | ✗     | ✗        | ✗       | ✗    |
| Delete any user           | ✓          | ✗     | ✗        | ✗       | ✗    |
| Delete organization       | ✓          | ✗     | ✗        | ✗       | ✗    |
| Create/update org          | ✓          | ✓     | ✗        | ✗       | ✗    |
| Admin statistics          | ✓          | ✓     | ✗        | ✗       | ✗    |
| Any org’s stats            | ✓          | ✓     | Own org  | Own org | ✗    |
| Create org users          | ✓          | ✓     | ✓ (OrgUser only) | ✗ | ✗    |
| Manage categories         | ✓ (any org)| ✓ (any org) | ✓ (own org) | Read only | ✗ |
| Upload/list/delete docs   | ✓ (any org)| ✓ (any org) | ✓ (own org) | ✓ (own org) | ✗ |
| Chat with documents       | ✓          | ✓     | ✓        | ✓       | ✗    |
| List users                | All        | All   | Own org  | Self    | Self |
| Update self (profile)     | ✓          | ✓     | ✓        | ✓       | ✓    |

---

## Who can act ON each role

| Role       | Can be created by              | Can be updated/activated/password/chat-limit by | Can be deleted by |
|-----------|--------------------------------|-------------------------------------------------|-------------------|
| SuperAdmin| SuperAdmin                     | SuperAdmin                                      | SuperAdmin (not self) |
| Admin     | SuperAdmin                     | SuperAdmin                                      | SuperAdmin        |
| OrgAdmin  | SuperAdmin, Admin, OrgAdmin (same org) | SuperAdmin, Admin only (user API)              | SuperAdmin        |
| OrgUser   | SuperAdmin, Admin, OrgAdmin (same org) | SuperAdmin, Admin only (user API)               | SuperAdmin        |
| User      | Self (signup), SuperAdmin, Admin | SuperAdmin, Admin only                          | SuperAdmin        |

Use this file together with `SYSTEM_DESIGN_DOCUMENT.md` to implement role-based dashboards and feature flags in the UI.
