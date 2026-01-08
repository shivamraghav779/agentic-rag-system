# Frontend Implementation Guide

## Overview

This document provides comprehensive guidance for frontend developers to implement the AI Business Knowledge System. It includes API endpoints, UI component suggestions, placement recommendations, and dashboard wireframes.

## Base Configuration

- **Base URL**: `http://localhost:8000/api/v1` (development)
- **Authentication**: Bearer Token (JWT)
- **Content-Type**: `application/json` (except file uploads: `multipart/form-data`)

## Authentication Flow

### 1. User Registration
**API**: `POST /api/v1/auth/signup`

**UI Placement**: 
- Landing page or separate signup page
- Modal dialog on login page

**Suggested Component**: `SignupForm`
```typescript
interface SignupForm {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}
```

**UI Elements**:
- Input fields: Username, Email, Password, Confirm Password
- Submit button
- Link to login page
- Success message/toast after registration

---

### 2. User Login
**API**: `POST /api/v1/auth/login`

**UI Placement**: 
- Login page (main entry point)
- Modal dialog

**Suggested Component**: `LoginForm`
```typescript
interface LoginForm {
  email: string;
  password: string;
}
```

**UI Elements**:
- Email input
- Password input (with show/hide toggle)
- "Remember me" checkbox (optional)
- Submit button
- "Forgot password" link (if implemented)
- Link to signup page
- Error message display

**After Login**:
- Store `access_token` and `refresh_token` in localStorage/sessionStorage
- Redirect to appropriate dashboard based on user role

---

### 3. Get Current User
**API**: `GET /api/v1/auth/me`

**UI Placement**: 
- User profile dropdown/menu
- Dashboard header
- Settings page

**Suggested Component**: `UserProfile`
- Display: Username, Email, Role, Organization (if applicable)
- Show user avatar/initial
- Link to profile settings

---

### 4. Refresh Token
**API**: `POST /api/v1/auth/refresh`

**UI Placement**: 
- Background interceptor (automatic)
- Should be called automatically before access token expires

**Implementation**: 
- Create an axios interceptor or fetch wrapper
- Automatically refresh token when 401 is received
- Retry original request with new token

---

### 5. Update System Prompt
**API**: `PATCH /api/v1/auth/me/system-prompt`

**UI Placement**: 
- User settings/preferences page
- Profile settings section

**Suggested Component**: `SystemPromptEditor`
- Textarea for custom prompt
- Save button
- Preview/reset button
- Help text explaining what system prompt does

---

## Dashboard Layouts

### User Dashboard (Private User - USER role)

**API**: `GET /api/v1/statistics/user`

**Wireframe**:
```
┌─────────────────────────────────────────────────────────┐
│  Header: Logo | User Menu (Profile, Settings, Logout)   │
├─────────────────────────────────────────────────────────┤
│  Welcome, [Username]                                     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Total Docs   │  │ Conversations│  │ Total Chats  │  │
│  │      0       │  │      0       │  │      0       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ Tokens Used  │  │ Chats Today   │                    │
│  │      0       │  │  0 / 3        │                    │
│  └──────────────┘  └──────────────┘                    │
│                                                          │
│  Recent Activity                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ No activity yet                                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Note: Private users cannot upload documents or chat.   │
│  Join an organization to access these features.         │
└─────────────────────────────────────────────────────────┘
```

**UI Components**:
- `StatCard`: Reusable card component for displaying statistics
- `ActivityFeed`: List component for recent activity
- `InfoBanner`: Notice about private user limitations

**Suggested Component Structure**:
```typescript
<UserDashboard>
  <DashboardHeader user={user} />
  <StatsGrid>
    <StatCard title="Total Documents" value={stats.total_documents} />
    <StatCard title="Conversations" value={stats.total_conversations} />
    <StatCard title="Total Chats" value={stats.total_chats} />
    <StatCard title="Tokens Used" value={stats.total_tokens_used} />
    <StatCard title="Chats Today" value={`${stats.chats_today} / ${stats.chat_limit}`} />
  </StatsGrid>
  <ActivityFeed activities={stats.recent_activity} />
</UserDashboard>
```

---

### Organization User Dashboard (ORG_ADMIN, ORG_USER)

**API**: `GET /api/v1/statistics/user`

**Wireframe**:
```
┌─────────────────────────────────────────────────────────┐
│  Header: Logo | Org: [Org Name] | User Menu            │
├─────────────────────────────────────────────────────────┤
│  Dashboard                                                │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ My Documents │  │ Conversations│  │ My Chats    │  │
│  │      5       │  │     10       │  │     25       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Tokens Used  │  │ Chats Today  │  │ Remaining    │  │
│  │   15,000     │  │  2 / 10      │  │     8        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  Documents by Category                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ HR: 2  |  Sales: 1  |  Legal: 1  |  General: 1 │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Recent Activity                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 📄 Uploaded: policy.pdf (2 hours ago)            │  │
│  │ 💬 Chatted with: handbook.pdf (1 hour ago)      │  │
│  │ 📄 Uploaded: contract.docx (3 hours ago)          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Quick Actions                                           │
│  [Upload Document]  [New Chat]  [View Documents]        │
└─────────────────────────────────────────────────────────┘
```

**UI Components**:
- `StatCard`: Statistics cards
- `CategoryChart`: Bar chart or pie chart for documents by category
- `ActivityFeed`: Recent activity timeline
- `QuickActionButtons`: Action buttons for common tasks

**Suggested Component Structure**:
```typescript
<OrgUserDashboard>
  <DashboardHeader organization={org} user={user} />
  <StatsGrid>
    <StatCard title="My Documents" value={stats.total_documents} icon="📄" />
    <StatCard title="Conversations" value={stats.total_conversations} icon="💬" />
    <StatCard title="My Chats" value={stats.total_chats} icon="💭" />
    <StatCard title="Tokens Used" value={formatNumber(stats.total_tokens_used)} icon="🔢" />
    <StatCard title="Chats Today" value={`${stats.chats_today} / ${stats.chat_limit}`} icon="📊" />
    <StatCard title="Remaining" value={stats.chats_remaining_today} icon="⏱️" />
  </StatsGrid>
  <CategoryBreakdown data={stats.documents_by_category} />
  <ActivityFeed activities={stats.recent_activity} />
  <QuickActions>
    <Button onClick={uploadDocument}>Upload Document</Button>
    <Button onClick={newChat}>New Chat</Button>
    <Button onClick={viewDocuments}>View Documents</Button>
  </QuickActions>
</OrgUserDashboard>
```

---

### Organization Admin Dashboard (ORG_ADMIN)

**API**: `GET /api/v1/statistics/organization/{organization_id}`

**Wireframe**:
```
┌─────────────────────────────────────────────────────────┐
│  Header: Logo | Org: [Org Name] | Admin Menu            │
├─────────────────────────────────────────────────────────┤
│  Organization Dashboard                                 │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Total Users  │  │ Total Docs   │  │ Conversations│  │
│  │     50       │  │    100       │  │     200       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Total Chats  │  │ Active Users │  │ Tokens Used  │  │
│  │    500       │  │     45       │  │  500,000     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  Documents by Category                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  [Bar Chart]                                     │  │
│  │  HR: 30  |  Sales: 40  |  Legal: 20  |  ...     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Users by Role                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Org Admin: 2  |  Org User: 48                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Recent Activity                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 👤 john_doe uploaded: policy.pdf (1 hour ago)   │  │
│  │ 👤 jane_smith chatted with: handbook.pdf         │  │
│  │ 👤 New user created: employee_50 (2 hours ago)  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Management Actions                                      │
│  [Manage Users]  [Upload Document]  [View Documents]     │
└─────────────────────────────────────────────────────────┘
```

**UI Components**:
- `OrgStatsGrid`: Grid of organization statistics
- `CategoryChart`: Visual chart for documents by category
- `RoleDistribution`: Display users by role
- `ActivityFeed`: Organization-wide activity
- `ManagementPanel`: Quick access to management functions

**Suggested Component Structure**:
```typescript
<OrgAdminDashboard>
  <DashboardHeader organization={org} user={user} />
  <OrgStatsGrid>
    <StatCard title="Total Users" value={stats.total_users} />
    <StatCard title="Total Documents" value={stats.total_documents} />
    <StatCard title="Conversations" value={stats.total_conversations} />
    <StatCard title="Total Chats" value={stats.total_chats} />
    <StatCard title="Active Users" value={stats.active_users} />
    <StatCard title="Tokens Used" value={formatNumber(stats.total_tokens_used)} />
  </OrgStatsGrid>
  <CategoryChart data={stats.documents_by_category} />
  <RoleDistribution data={stats.users_by_role} />
  <ActivityFeed activities={stats.recent_activity} />
  <ManagementPanel>
    <Button onClick={manageUsers}>Manage Users</Button>
    <Button onClick={uploadDocument}>Upload Document</Button>
    <Button onClick={viewDocuments}>View Documents</Button>
  </ManagementPanel>
</OrgAdminDashboard>
```

---

### Admin Dashboard (ADMIN, SUPER_ADMIN)

**API**: `GET /api/v1/statistics/admin`

**Wireframe**:
```
┌─────────────────────────────────────────────────────────┐
│  Header: Logo | Admin Panel | User Menu                 │
├─────────────────────────────────────────────────────────┤
│  System Dashboard                                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Organizations│  │ Total Users  │  │ Total Docs   │  │
│  │     10       │  │    500       │  │   1,000      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Conversations│  │ Total Chats  │  │ Tokens Used  │  │
│  │   2,000      │  │   5,000     │  │  5,000,000   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ Active Orgs  │  │ Active Users │                    │
│  │      9       │  │     450       │                    │
│  └──────────────┘  └──────────────┘                    │
│                                                          │
│  Users by Role                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Super Admin: 1  |  Admin: 5  |  Org Admin: 20   │  │
│  │  Org User: 450  |  User: 24                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Documents by Category                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  [Bar Chart]                                     │  │
│  │  HR: 300  |  Sales: 400  |  Legal: 200  |  ...  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Organizations Overview                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Acme Corp: 50 users, 100 docs                   │  │
│  │  Tech Corp: 30 users, 80 docs                     │  │
│  │  ... (expandable list)                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Recent System Activity                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 🏢 New organization: Tech Corp (1 hour ago)       │  │
│  │ 👤 New user: admin@techcorp.com (2 hours ago)      │  │
│  │ 📄 john@acme.com uploaded: policy.pdf           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Admin Actions                                           │
│  [Manage Organizations]  [Manage Users]  [System Settings]│
└─────────────────────────────────────────────────────────┘
```

**UI Components**:
- `SystemStatsGrid`: System-wide statistics
- `RoleDistributionChart`: Visual representation of users by role
- `CategoryChart`: Documents by category
- `OrganizationsList`: Expandable list of organizations with stats
- `SystemActivityFeed`: System-wide activity timeline
- `AdminActionsPanel`: Quick access to admin functions

**Suggested Component Structure**:
```typescript
<AdminDashboard>
  <DashboardHeader user={user} />
  <SystemStatsGrid>
    <StatCard title="Organizations" value={stats.total_organizations} />
    <StatCard title="Total Users" value={stats.total_users} />
    <StatCard title="Total Documents" value={stats.total_documents} />
    <StatCard title="Conversations" value={stats.total_conversations} />
    <StatCard title="Total Chats" value={stats.total_chats} />
    <StatCard title="Tokens Used" value={formatNumber(stats.total_tokens_used)} />
    <StatCard title="Active Orgs" value={stats.active_organizations} />
    <StatCard title="Active Users" value={stats.active_users} />
  </SystemStatsGrid>
  <RoleDistributionChart data={stats.users_by_role} />
  <CategoryChart data={stats.documents_by_category} />
  <OrganizationsList organizations={stats.organizations_stats} />
  <SystemActivityFeed activities={stats.recent_activity} />
  <AdminActionsPanel>
    <Button onClick={manageOrganizations}>Manage Organizations</Button>
    <Button onClick={manageUsers}>Manage Users</Button>
    <Button onClick={systemSettings}>System Settings</Button>
  </AdminActionsPanel>
</AdminDashboard>
```

---

## Document Management

### Upload Document
**API**: `POST /api/v1/documents/upload`

**UI Placement**: 
- Documents page
- Dashboard quick action
- Modal dialog

**Suggested Component**: `DocumentUpload`
```typescript
interface DocumentUploadProps {
  organizationId?: number;
  category?: DocumentCategory;
  onSuccess: (document: DocumentInfo) => void;
}
```

**UI Elements**:
- File input (drag & drop support)
- Category selector dropdown
- Organization selector (if user has access to multiple orgs)
- Upload progress bar
- Success/error messages
- File preview (if applicable)

**Wireframe**:
```
┌─────────────────────────────────────────┐
│  Upload Document                        │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Drag & Drop files here            │ │
│  │  or click to browse                │ │
│  │                                    │ │
│  │  Supported: PDF, DOCX, TXT, HTML   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Category: [Dropdown: HR/Sales/Legal...] │
│                                         │
│  Organization: [Auto-selected/Disabled]│
│                                         │
│  [Cancel]  [Upload]                     │
└─────────────────────────────────────────┘
```

---

### List Documents
**API**: `GET /api/v1/documents`

**UI Placement**: 
- Documents page (main view)
- Sidebar navigation

**Suggested Component**: `DocumentsList`
```typescript
interface DocumentsListProps {
  organizationId?: number;
  category?: DocumentCategory;
  onDocumentSelect: (document: DocumentInfo) => void;
}
```

**UI Elements**:
- Search/filter bar
- Category filter chips
- Organization filter (if applicable)
- Document cards/grid view
- List view toggle
- Pagination
- Sort options (date, name, size)

**Wireframe**:
```
┌─────────────────────────────────────────────────────────┐
│  Documents                                              │
├─────────────────────────────────────────────────────────┤
│  [Search...]  [Filter: All Categories ▼]  [Sort: Date ▼]│
│                                                          │
│  Category Filters: [All] [HR] [Sales] [Legal] [Ops]     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 📄 policy.pdf│  │ 📄 handbook  │  │ 📄 contract  │  │
│  │ HR • 2.5 MB  │  │ General     │  │ Legal        │  │
│  │ Uploaded:     │  │ 1.2 MB      │  │ 3.1 MB       │  │
│  │ 2 hours ago   │  │ 5 hours ago │  │ 1 day ago    │  │
│  │ [View] [Chat] │  │ [View] [Chat]│  │ [View] [Chat]│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  [Previous]  Page 1 of 5  [Next]                         │
└─────────────────────────────────────────────────────────┘
```

---

### Get Document
**API**: `GET /api/v1/documents/{document_id}`

**UI Placement**: 
- Document detail page
- Modal dialog

**Suggested Component**: `DocumentDetail`
- Document metadata display
- Download button
- Delete button (if user has permission)
- Chat button
- View conversations button

---

### Delete Document
**API**: `DELETE /api/v1/documents/{document_id}`

**UI Placement**: 
- Document detail page
- Documents list (with confirmation)

**Suggested Component**: `DeleteDocumentDialog`
- Confirmation message
- Warning about permanent deletion
- Cancel/Delete buttons

---

## Chat Interface

### Chat with Document
**API**: `POST /api/v1/chat`

**UI Placement**: 
- Chat page (main interface)
- Sidebar chat panel
- Modal dialog

**Suggested Component**: `ChatInterface`
```typescript
interface ChatInterfaceProps {
  documentId: number;
  conversationId?: number;
  onNewConversation: () => void;
}
```

**UI Elements**:
- Document info header
- Conversation title
- Chat messages list (scrollable)
- Input area with send button
- Source documents display
- Token usage indicator
- Rate limit warning

**Wireframe**:
```
┌─────────────────────────────────────────────────────────┐
│  📄 policy.pdf  |  Conversation: "HR Policies Q&A"      │
│  [New Chat] [View Document] [Settings]                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Chat Messages (Scrollable)                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │ You: What is the leave policy?                  │  │
│  │ [2 hours ago]                                    │  │
│  │                                                  │  │
│  │ AI: According to the policy document...        │  │
│  │ [Source: policy.pdf, page 5]                     │  │
│  │ [2 hours ago]                                    │  │
│  │                                                  │  │
│  │ You: How many days of annual leave?             │  │
│  │ [1 hour ago]                                     │  │
│  │                                                  │  │
│  │ AI: Employees are entitled to 20 days...        │  │
│  │ [Source: policy.pdf, page 6]                     │  │
│  │ [1 hour ago]                                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Type your question...              [Send]        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Chats remaining today: 8 / 10                          │
└─────────────────────────────────────────────────────────┘
```

**Component Structure**:
```typescript
<ChatInterface>
  <ChatHeader document={document} conversation={conversation} />
  <ChatMessages messages={messages} />
  <ChatInput 
    onSubmit={handleChat}
    disabled={rateLimitExceeded}
    placeholder="Ask a question about this document..."
  />
  <RateLimitIndicator remaining={remainingChats} />
</ChatInterface>
```

---

### Chat History
**API**: `GET /api/v1/chat/history`

**UI Placement**: 
- Chat history sidebar
- Separate history page
- User profile section

**Suggested Component**: `ChatHistoryList`
- Filter by document or conversation
- Search functionality
- Date grouping
- Expandable conversation items

---

### Conversations
**API**: `GET /api/v1/chat/conversations`

**UI Placement**: 
- Sidebar navigation
- Conversations page

**Suggested Component**: `ConversationsList`
- List of conversations with titles
- Document association
- Last activity timestamp
- Click to open conversation

**Wireframe**:
```
┌─────────────────────────────────────────┐
│  Conversations                          │
├─────────────────────────────────────────┤
│  [New Conversation]                     │
│                                         │
│  📄 HR Policies Q&A                     │
│  policy.pdf • 2 hours ago               │
│                                         │
│  📄 Contract Questions                  │
│  contract.docx • 1 day ago              │
│                                         │
│  📄 Sales Process                       │
│  handbook.pdf • 3 days ago              │
│                                         │
└─────────────────────────────────────────┘
```

---

## User Management (Admin/OrgAdmin)

### List Users
**API**: `GET /api/v1/users`

**UI Placement**: 
- Users management page
- Admin panel

**Suggested Component**: `UsersTable`
- Data table with sorting/filtering
- Role filter
- Organization filter
- Search functionality
- Actions column (Edit, Delete, Activate)

**Wireframe**:
```
┌─────────────────────────────────────────────────────────┐
│  Users Management                                       │
├─────────────────────────────────────────────────────────┤
│  [Add User]  [Search...]  [Filter: All Roles ▼]        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Username  │ Email        │ Role      │ Status    │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ john_doe  │ john@...     │ Org User  │ Active    │ │
│  │           │              │           │ [Edit]    │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ jane_smith│ jane@...     │ Org Admin │ Active    │ │
│  │           │              │           │ [Edit]    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  [Previous]  Page 1 of 10  [Next]                         │
└─────────────────────────────────────────────────────────┘
```

---

### Create/Update User
**API**: `POST /api/v1/users` or `PATCH /api/v1/users/{user_id}`

**UI Placement**: 
- Modal dialog
- Separate form page

**Suggested Component**: `UserForm`
- Form fields: Username, Email, Password, Role, Organization
- Validation
- Save/Cancel buttons

---

## Organization Management (Admin)

### List Organizations
**API**: `GET /api/v1/organizations`

**UI Placement**: 
- Organizations page
- Admin panel

**Suggested Component**: `OrganizationsList`
- Organization cards or table
- Active/Inactive status
- User count
- Document count
- Actions (Edit, Delete, View Stats)

---

### Create Organization
**API**: `POST /api/v1/organizations`

**UI Placement**: 
- Modal dialog
- Separate form page

**Suggested Component**: `OrganizationForm`
- Organization details form
- Admin user creation form (embedded)
- Save/Cancel buttons

---

## Statistics/Dashboard APIs

### User Statistics
**API**: `GET /api/v1/statistics/user`

**UI Placement**: 
- User dashboard (main view)
- Profile page statistics section

**Component**: `UserStatsDashboard` (see dashboard wireframes above)

---

### Organization Statistics
**API**: `GET /api/v1/statistics/organization/{organization_id}`

**UI Placement**: 
- Organization admin dashboard
- Organization detail page

**Component**: `OrganizationStatsDashboard` (see dashboard wireframes above)

---

### Admin Statistics
**API**: `GET /api/v1/statistics/admin`

**UI Placement**: 
- Admin dashboard (main view)
- System overview page

**Component**: `AdminStatsDashboard` (see dashboard wireframes above)

---

## Suggested UI Component Library

### Recommended Libraries

1. **UI Framework**:
   - Material-UI (MUI)
   - Ant Design
   - Chakra UI
   - Tailwind CSS + Headless UI

2. **Charts/Visualizations**:
   - Recharts
   - Chart.js
   - Victory
   - ApexCharts

3. **Data Tables**:
   - Material-UI DataGrid
   - TanStack Table (React Table)
   - AG Grid

4. **Forms**:
   - React Hook Form
   - Formik
   - React Final Form

5. **File Upload**:
   - react-dropzone
   - react-file-upload

6. **State Management**:
   - React Query / TanStack Query (for server state)
   - Zustand / Redux (for client state)

---

## Common UI Components to Build

### 1. StatCard
```typescript
interface StatCardProps {
  title: string;
  value: string | number;
  icon?: string;
  trend?: 'up' | 'down' | 'neutral';
  onClick?: () => void;
}
```

### 2. ActivityFeed
```typescript
interface ActivityFeedProps {
  activities: ActivityItem[];
  limit?: number;
  showUser?: boolean;
  showOrganization?: boolean;
}
```

### 3. DocumentCard
```typescript
interface DocumentCardProps {
  document: DocumentInfo;
  onView: () => void;
  onChat: () => void;
  onDelete?: () => void;
  showActions?: boolean;
}
```

### 4. ChatMessage
```typescript
interface ChatMessageProps {
  message: ChatHistoryResponse;
  isUser: boolean;
  showTimestamp: boolean;
  showSources: boolean;
}
```

### 5. CategoryFilter
```typescript
interface CategoryFilterProps {
  selected: DocumentCategory | 'all';
  onChange: (category: DocumentCategory | 'all') => void;
}
```

### 6. RateLimitIndicator
```typescript
interface RateLimitIndicatorProps {
  used: number;
  limit: number;
  resetTime?: Date;
}
```

---

## Navigation Structure

### Main Navigation (Sidebar/Menu)

```
Dashboard
├── Home (User Dashboard)
├── Documents
│   ├── All Documents
│   ├── Upload Document
│   └── By Category
├── Chat
│   ├── New Chat
│   ├── Conversations
│   └── History
└── Settings
    ├── Profile
    ├── System Prompt
    └── Preferences

[If OrgAdmin/Admin]
├── Organization
│   ├── Overview
│   ├── Users
│   └── Settings
└── Analytics

[If Admin/SuperAdmin]
├── Admin Panel
│   ├── Organizations
│   ├── Users
│   ├── System Stats
│   └── Settings
```

---

## API Response Handling

### Error Handling

All APIs return standard HTTP status codes. Handle errors appropriately:

```typescript
// Example error handling
try {
  const response = await api.post('/api/v1/chat', data);
  return response.data;
} catch (error) {
  if (error.response?.status === 401) {
    // Refresh token and retry
    await refreshToken();
    return retryRequest();
  } else if (error.response?.status === 403) {
    // Show access denied message
    showError('Access denied');
  } else if (error.response?.status === 429) {
    // Show rate limit message
    showError('Rate limit exceeded. Please try again later.');
  } else {
    // Show generic error
    showError(error.response?.data?.detail || 'An error occurred');
  }
}
```

### Token Management

```typescript
// Store tokens
localStorage.setItem('access_token', token.access_token);
localStorage.setItem('refresh_token', token.refresh_token);

// Include in requests
headers: {
  'Authorization': `Bearer ${access_token}`
}

// Auto-refresh on 401
if (response.status === 401) {
  const newToken = await refreshToken();
  // Retry original request
}
```

---

## State Management Recommendations

### Server State (API Data)
- Use **React Query** or **TanStack Query**
- Automatic caching, refetching, and synchronization
- Example:
```typescript
const { data: stats, isLoading } = useQuery(
  ['userStats'],
  () => api.get('/api/v1/statistics/user')
);
```

### Client State (UI State)
- Use **Zustand** or **Context API** for simple state
- Use **Redux** for complex state management

### Form State
- Use **React Hook Form** for form management
- Minimal re-renders, built-in validation

---

## Responsive Design Considerations

### Breakpoints
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

### Mobile Adaptations
- Collapsible sidebar navigation
- Stack statistics cards vertically
- Full-width chat interface
- Bottom navigation for mobile
- Swipe gestures for document cards

---

## Accessibility Requirements

1. **Keyboard Navigation**: All interactive elements should be keyboard accessible
2. **Screen Readers**: Proper ARIA labels and roles
3. **Color Contrast**: WCAG AA compliance
4. **Focus Indicators**: Visible focus states
5. **Alt Text**: Images and icons should have descriptive alt text

---

## Performance Optimization

1. **Lazy Loading**: Load dashboard components on demand
2. **Pagination**: Implement pagination for large lists
3. **Virtual Scrolling**: For long chat history lists
4. **Debouncing**: For search inputs
5. **Caching**: Cache API responses using React Query
6. **Code Splitting**: Split routes and heavy components

---

## Testing Recommendations

1. **Unit Tests**: Test individual components
2. **Integration Tests**: Test API integration
3. **E2E Tests**: Test complete user flows
4. **Visual Regression**: Test UI consistency

---

## Example API Integration Code

### React Hook Example

```typescript
// hooks/useAuth.ts
export const useAuth = () => {
  const login = async (email: string, password: string) => {
    const response = await api.post('/api/v1/auth/login', {
      email,
      password
    });
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  };

  return { login, logout };
};

// hooks/useStatistics.ts
export const useUserStatistics = () => {
  return useQuery(
    ['userStats'],
    () => api.get('/api/v1/statistics/user'),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

// hooks/useChat.ts
export const useChat = () => {
  const queryClient = useQueryClient();
  
  const sendMessage = useMutation(
    (data: ChatRequest) => api.post('/api/v1/chat', data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['chatHistory']);
        queryClient.invalidateQueries(['userStats']);
      }
    }
  );

  return { sendMessage };
};
```

---

## Color Scheme Suggestions

### Primary Colors
- **Primary**: Blue (#2563eb) - Actions, links
- **Success**: Green (#10b981) - Success messages, positive stats
- **Warning**: Yellow (#f59e0b) - Warnings, rate limits
- **Error**: Red (#ef4444) - Errors, deletions
- **Info**: Cyan (#06b6d4) - Information messages

### Dashboard Colors
- **Stat Cards**: Light backgrounds with colored borders/icons
- **Charts**: Use distinct colors for different categories
- **Activity Feed**: Alternating row colors for readability

---

## Icon Suggestions

- 📄 Documents
- 💬 Chat/Conversations
- 👤 Users
- 🏢 Organizations
- 📊 Statistics
- ⚙️ Settings
- 📤 Upload
- 🔍 Search
- ➕ Add/Create
- ✏️ Edit
- 🗑️ Delete
- ✅ Active
- ❌ Inactive

---

## Loading States

All API calls should show loading indicators:

1. **Skeleton Screens**: For initial page loads
2. **Spinners**: For button actions
3. **Progress Bars**: For file uploads
4. **Skeleton Cards**: For lists loading

---

## Empty States

Design empty states for:
- No documents
- No conversations
- No chat history
- No users (for org admin)
- No organizations (for admin)

Include helpful messages and call-to-action buttons.

---

This guide provides everything needed to implement the frontend. For specific API details, refer to `CRUD_API_DOCUMENTATION.md`.

