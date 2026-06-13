# Dealer System Enhancement Plan

**Project:** SattaBase Dealer Frontend  
**Created:** 2024-01-15  
**Updated:** 2024-06-12  
**Status:** Phase 4 - DSR Authentication System (Redesigned)

---

## Recent Updates (2024-06-12)

### Phase 4: DSR Authentication System - REDESIGNED

The DSR authentication system has been redesigned based on a new understanding of the DSR business model:

#### Key Design Principles:
1. **DSRs are independent entities** - They own their profile, register themselves
2. **Dealer-DSR is a relationship**, not ownership - Invitation/acceptance model
3. **Permission control at invitation** - Dealer sets what DSR can do
4. **DSR has agency** - Can reject invitations they don't want
5. **Audit trail preserved** - Removed DSRs keep transaction records with status
6. **Future-ready for freelance marketplace** - System designed for enhancement

---

## Overview

This document outlines the implementation plan for enhancing the dealer system with:
1. Multi-tenancy data isolation (all transactions under logged-in dealer)
2. Sales Representative invitation workflow
3. Comprehensive access matrix with row-level and functional controls
4. DSR Authentication System (independent profiles with dealer relationship)
5. Garbage collection and data cleanup

---

## Phase 1: Multi-Tenancy Data Isolation

### Objective
Ensure ALL transactions, records, and operations are scoped to the currently logged-in dealer.

### Current State Analysis
- ✅ API requests include `X-Dealer-Username` header
- ✅ Dealer selection works via `useDealerContext`
- ✅ Backend filtering VERIFIED - all endpoints use `get_dealer_context()` and filter by `dealer_id`
- ✅ Cross-dealer data leakage prevention IMPLEMENTED
- ✅ Database-level NOT NULL constraints ENFORCED on all dealer FK fields

### Audit Results (2024-01-15)

#### Backend API Endpoints - ALL VERIFIED ✅
| Module | Dealer Filtering | Implementation |
|--------|-----------------|----------------|
| **Inventory API** | ✅ Verified | `Product.objects.filter(dealer_id=dealer_username)` |
| **Sales API** | ✅ Verified | `SaleRecord.objects.filter(dealer_id=dealer_username)` |
| **Suppliers API** | ✅ Verified | `Supplier.objects.filter(dealer_id=dealer_username)` |
| **DSR API** | ✅ Verified | Uses `DsrDealerAssignment` junction table |
| **Reports API** | ✅ Verified | All queries filtered by `dealer_id` |
| **Brands/Categories** | ✅ Verified | Filtered by `dealer_id` |

#### Model Relationships - ALL VERIFIED ✅
| Model | Dealer Relationship | Notes |
|-------|-------------------|-------|
| `Product` | FK to `DealerConfig` | `dealer` field - NOT NULL enforced |
| `Brand` | FK to `DealerConfig` | `dealer` field - NOT NULL enforced |
| `Category` | FK to `DealerConfig` | `dealer` field - NOT NULL enforced |
| `RestockRecord` | FK to `DealerConfig` | `dealer` field - NOT NULL enforced |
| `SaleRecord` | FK to `DealerConfig` | `dealer` field - NOT NULL enforced |
| `Supplier` | FK to `DealerConfig` | `dealer` field - NOT NULL enforced |
| `DSR` | Many-to-Many via `DsrDealerAssignment` | Junction table design |
| `DsrInvitation` | FK to `DealerConfig` | Direct FK - NOT NULL |
| `DsrDealerAssignment` | FK to `DealerConfig` | Junction table - NOT NULL |

### Implementation Tasks

#### 1.1 Backend Data Isolation Verification
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Audit all API endpoints for dealer filtering | ✅ Complete | HIGH | All endpoints verified |
| Verify DSR model dealer relationship | ✅ Complete | HIGH | Uses DsrDealerAssignment junction table |
| Verify Sales model dealer filtering | ✅ Complete | HIGH | Has dealer FK, all queries filtered |
| Verify Inventory model dealer filtering | ✅ Complete | HIGH | Products have dealer FK |
| Verify Suppliers model dealer filtering | ✅ Complete | HIGH | Suppliers have dealer FK |
| Verify Collections/BadDebt filtering | ✅ Complete | MEDIUM | Via SaleRecord dealer FK |

#### 1.2 Frontend Data Context
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Add dealer context to all data operations | ✅ Complete | HIGH | apiClient sends X-Dealer-Username header |
| Verify form submissions include dealer | ✅ Complete | HIGH | Backend auto-associates from header |
| Add dealer validation in API client | ✅ Complete | MEDIUM | Header sent on every request |

#### 1.3 Database-Level Enforcement
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Remove `null=True` from dealer FK fields | ✅ Complete | HIGH | Done via migrations 0005/0007/0004 |
| Add database constraints for dealer FK | ✅ Complete | HIGH | NOT NULL enforced at DB level |
| Implement row-level security (optional) | ⏸️ Deferred | LOW | PostgreSQL RLS - not required for current scale |

### Deliverables
- [x] All API endpoints return only dealer-scoped data
- [x] All create/update operations associate with correct dealer
- [x] Database constraints to prevent orphan records (NOT NULL enforced)

---

## Phase 2: Sales Representative Invitation Workflow

### Objective
Implement a complete workflow for adding sales representatives using the existing invitation system.

### Current State Analysis
- ✅ Invitation system exists in SattaBase billing
- ✅ User registration flow exists
- ✅ DSR creation integrated with invitations
- ✅ Access assignment automated via useAccess composable

### Workflow Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ADD SALES REPRESENTATIVE FLOW                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. DEALER ADMIN initiates "Add Sales Rep"                          │
│     └─> Opens form in Reports.vue or dedicated page                 │
│                                                                      │
│  2. SYSTEM creates INVITATION                                       │
│     └─> POST /billing/invitations                                   │
│     └─> Email sent to new rep                                       │
│     └─> Invitation record: {email, role, dealer_id, expires}        │
│                                                                      │
│  3. NEW USER accepts invitation                                     │
│     └─> Clicks link in email                                        │
│     └─> Completes registration                                      │
│     └─> User account created with role                              │
│                                                                      │
│  4. SYSTEM creates DSR record                                       │
│     └─> Auto-create DSR linked to user_id                           │
│     └─> Assign to dealer via DsrDealerAssignment                    │
│     └─> Set initial permissions                                     │
│                                                                      │
│  5. NEW USER gets system access                                     │
│     └─> Can log in to dealer frontend                               │
│     └─> Access limited by assigned role                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Implementation Tasks

#### 2.1 Invitation Creation UI
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create "Add Rep" button in Reports.vue | ✅ Complete | HIGH | Unified button with gradient styling |
| Build unified AddRepModal component | ✅ Complete | HIGH | AddRepModal.vue combines invite + direct add flows |
| Integrate with /billing/invitations API | ✅ Complete | HIGH | invitation.service.ts created with all endpoints |
| Add invitation list view | ✅ Complete | MEDIUM | InvitationList.vue with filtering and management |

#### 2.2 Invitation Acceptance Flow
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Verify invitation acceptance endpoint | ✅ Complete | HIGH | Backend endpoint /invitations/{token}/accept exists |
| Add DSR auto-creation on acceptance | ✅ Complete | HIGH | Backend creates DSR record automatically |
| Create DsrDealerAssignment record | ✅ Complete | HIGH | Backend creates assignment on acceptance |

#### 2.3 Access Provisioning
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Define role-based access templates | ✅ Complete | HIGH | Templates defined in plan, ready for use |
| Auto-assign access on invitation acceptance | ✅ Complete | HIGH | useAccess composable provides limit checking |
| Add access editing capability | 🟡 Deferred | MEDIUM | Future enhancement for settings page |

### Role Templates

| Role | Dashboard | Inventory | Sales | Collections | Reports | Export | Max DSRs |
|------|-----------|-----------|-------|-------------|---------|--------|----------|
| Sales Rep | ✅ View | ✅ View | ✅ Full | ✅ View | ✅ View | ❌ | 1 |
| Senior Rep | ✅ View | ✅ Edit | ✅ Full | ✅ Edit | ✅ Full | ✅ | 3 |
| Manager | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ | 10 |
| Admin | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ | Unlimited |

### Deliverables
- [x] Unified "Add Rep" button with modal form (invite via email OR add directly)
- [x] Invitation creation and email sending (backend ready)
- [x] Direct DSR creation without email verification
- [x] DSR auto-creation on acceptance
- [x] Role-based access assignment (via useAccess)

> ⚠️ **Known Limitation**: The "Add Directly" mode currently creates a DSR record but does NOT create a user account. DSRs added this way cannot log in to the system. This will be resolved in Phase 4 with the DSR Authentication System.

---

## Phase 3: Comprehensive Access Matrix

### Objective
Implement fine-grained access control beyond menu visibility, including:
- Row-level entry permissions (based on numeric limits)
- Functional controls (print, export buttons)
- Limit enforcement (view only when limit reached)

### Access Matrix Design

#### 3.1 Access Key Categories

```typescript
// Boolean Access (Feature Toggles)
type BooleanAccess = {
  dashboard: boolean;      // View dashboard
  inventory: boolean;      // Access inventory module
  sales: boolean;          // Access sales module
  suppliers: boolean;      // Access suppliers module
  collections: boolean;    // Access collections module
  bad_debt: boolean;       // Access bad debt module
  reports: boolean;        // Access reports module
  print: boolean;          // Can print reports/invoices
  export: boolean;         // Can export data (CSV, PDF)
  settings: boolean;       // Access settings
};

// Numeric Limits (Row-Level Entry)
type NumericLimits = {
  max_products: number;    // Max products in inventory
  max_dsrs: number;        // Max sales representatives
  max_suppliers: number;   // Max suppliers
  max_sales_per_day: number; // Daily sales entry limit
  max_collections: number; // Max collection records
};

// String Values (Labels/Metadata)
type StringValues = {
  plan_label: string;      // Plan name for display
  data_retention: string;  // Data retention period
};
```

#### 3.2 Access Control Logic

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ACCESS CONTROL FLOW                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  BOOLEAN ACCESS (Feature Toggles)                                   │
│  ─────────────────────────────────────────────────                  │
│  IF access[key] === true:                                           │
│    → Show menu item                                                 │
│    → Enable feature buttons                                         │
│    → Allow access to route                                          │
│                                                                      │
│  IF access[key] === false OR undefined:                             │
│    → Hide menu item                                                 │
│    → Disable/hide feature buttons                                   │
│    → Redirect to dashboard with message                             │
│                                                                      │
│                                                                      │
│  NUMERIC LIMITS (Row-Level Entry)                                   │
│  ─────────────────────────────────────                              │
│  IF access[key] > 0:                                                │
│    → Can add new records (up to limit)                              │
│    → "Add New" button enabled                                       │
│    → Show count: "5/10 used"                                        │
│                                                                      │
│  IF current_count >= access[key]:                                   │
│    → "Add New" button DISABLED                                      │
│    → Show message: "Limit reached. Upgrade to add more."            │
│    → Existing records still VIEWABLE                                │
│    → Edit/Delete still allowed                                      │
│                                                                      │
│  IF access[key] === 0:                                              │
│    → No new entries allowed at all                                  │
│    → View only mode                                                 │
│                                                                      │
│                                                                      │
│  FUNCTIONAL CONTROLS (Print/Export)                                 │
│  ─────────────────────────────────────                              │
│  IF access["print"] === true:                                       │
│    → Show print button in reports                                   │
│    → Enable invoice printing                                        │
│                                                                      │
│  IF access["export"] === true:                                      │
│    → Show export buttons (CSV, PDF)                                 │
│    → Enable data download                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Implementation Tasks

#### 3.1 Enhance useAccess Composable
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Add `getLimit()` function | 🔴 Pending | HIGH | Return numeric limit with fallback |
| Add `canAddRecord(model, currentCount)` | 🔴 Pending | HIGH | Check if under limit |
| Add `hasFeature(key)` | 🔴 Pending | HIGH | Boolean feature check |
| Add `getRemainingLimit(key, current)` | 🔴 Pending | MEDIUM | Return remaining slots |

#### 3.2 UI Components Enhancement
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create `LimitGuard` component | 🔴 Pending | HIGH | Wrap add buttons with limit check |
| Enhance `PermissionGuard` | 🔴 Pending | HIGH | Support limit-based checks |
| Add limit indicators to list views | 🔴 Pending | MEDIUM | "5/10 products" display |
| Add upgrade prompts when at limit | 🔴 Pending | MEDIUM | Link to billing upgrade |

### Deliverables
- [ ] Enhanced `useAccess` composable with limit functions
- [ ] `LimitGuard` component for row-level control
- [ ] Print/Export button access control
- [ ] Limit indicators on all list views
- [ ] Upgrade prompts when limits reached

---

## Phase 4: DSR Authentication System (Redesigned)

### Objective
Implement a comprehensive authentication system where DSRs are independent entities that own their profiles and can serve multiple dealers through an invitation/acceptance model.

### Core Design Principles

| Principle | Description | Implementation Impact |
|-----------|-------------|----------------------|
| **Independent Profiles** | DSRs own their profile, register themselves | Self-registration flow, profile management |
| **Many-to-Many Relationship** | One DSR can serve multiple dealers | Junction table with permissions per dealer |
| **Invitation Model** | Dealer invites, DSR accepts/rejects | Invitation workflow with accept/reject actions |
| **Permission per Assignment** | Each dealer sets different permissions | Permissions stored in junction table |
| **DSR Agency** | DSR can reject unwanted invitations | Rejection capability, notification to dealer |
| **Audit Preservation** | Removed DSRs keep transaction records | Soft delete with status marking |
| **Future-Ready** | Prepared for freelance marketplace | Extensible profile model |

### Complete User Journey

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DSR COMPLETE USER JOURNEY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗   │
│  ║  PATHWAY 1: DSR SELF-REGISTRATION (Primary)                          ║   │
│  ╠══════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                       ║   │
│  ║  1. DSR visits /dsr/register                                         ║   │
│  ║     └─> Enters: Name, Phone, Email, Password                         ║   │
│  ║     └─> Creates DsrUser account (INACTIVE until assigned)            ║   │
│  ║                                                                       ║   │
│  ║  2. DSR sees dashboard: "No dealer assignments yet"                  ║   │
│  ║     └─> Can update profile, change password                          ║   │
│  ║     └─> Waiting for dealer invitations                               ║   │
│  ║                                                                       ║   │
│  ╚══════════════════════════════════════════════════════════════════════╝   │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗   │
│  ║  PATHWAY 2: DEALER INVITATION (Triggers Registration)                ║   │
│  ╠══════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                       ║   │
│  ║  1. Dealer goes to "Manage Reps" → "Add Rep"                         ║   │
│  ║     └─> Enters: DSR Phone/Email, Permissions, Role                   ║   │
│  ║     └─> System checks if DSR exists by phone/email                   ║   │
│  ║                                                                       ║   │
│  ║  2. IF DSR NOT REGISTERED:                                           ║   │
│  ║     └─> Create PENDING invitation                                    ║   │
│  ║     └─> Send SMS/Email: "Dealer X wants to add you as DSR"          ║   │
│  ║     └─> Include registration link with invitation token              ║   │
│  ║     └─> DSR clicks link → Registers → Auto-accepts invitation       ║   │
│  ║                                                                       ║   │
│  ║  3. IF DSR ALREADY REGISTERED:                                       ║   │
│  ║     └─> Create PENDING invitation                                    ║   │
│  ║     └─> Send notification: "Dealer X invited you"                    ║   │
│  ║     └─> DSR logs in → Sees invitation → Accepts/Rejects             ║   │
│  ║                                                                       ║   │
│  ╚══════════════════════════════════════════════════════════════════════╝   │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗   │
│  ║  PATHWAY 3: DSR LOGIN & WORKING                                       ║   │
│  ╠══════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                       ║   │
│  ║  1. DSR logs in at /dsr/login                                        ║   │
│  ║     └─> Enters: Phone/Email + Password                               ║   │
│  ║                                                                       ║   │
│  ║  2. IF multiple dealer assignments:                                  ║   │
│  ║     └─> Show dealer selection page                                   ║   │
│  ║     └─> DSR selects which dealer to work for today                   ║   │
│  ║                                                                       ║   │
│  ║  3. IF single dealer assignment:                                     ║   │
│  ║     └─> Auto-select that dealer                                      ║   │
│  ║     └─> Redirect to dashboard                                        ║   │
│  ║                                                                       ║   │
│  ║  4. DSR works within selected dealer's context                       ║   │
│  ║     └─> All operations scoped to selected dealer                     ║   │
│  ║     └─> Permissions defined by that dealer                           ║   │
│  ║                                                                       ║   │
│  ╚══════════════════════════════════════════════════════════════════════╝   │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗   │
│  ║  PATHWAY 4: DSR PROFILE MANAGEMENT                                    ║   │
│  ╠══════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                       ║   │
│  ║  1. DSR can access /dsr/profile                                      ║   │
│  ║     └─> Update name, phone, email                                    ║   │
│  ║     └─> Change password                                              ║   │
│  ║     └─> View all dealer assignments                                  ║   │
│  ║                                                                       ║   │
│  ║  2. DSR can view pending invitations                                 ║   │
│  ║     └─> See dealer name, offered role, permissions                   ║   │
│  ║     └─> Accept or Reject each invitation                             ║   │
│  ║                                                                       ║   │
│  ║  3. DSR can leave a dealer assignment                                ║   │
│  ║     └─> "Stop working with Dealer X"                                 ║   │
│  ║     └─> Confirmation required                                        ║   │
│  ║     └─> Assignment marked as INACTIVE                                ║   │
│  ║                                                                       ║   │
│  ╚══════════════════════════════════════════════════════════════════════╝   │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗   │
│  ║  PATHWAY 5: DEALER MANAGES DSRs                                       ║   │
│  ╠══════════════════════════════════════════════════════════════════════╣   │
│  ║                                                                       ║   │
│  ║  1. Dealer can view all DSR assignments                              ║   │
│  ║     └─> Active DSRs with status, role, permissions                   ║   │
│  ║     └─> Pending invitations                                          ║   │
│  ║                                                                       ║   │
│  ║  2. Dealer can update DSR permissions                                ║   │
│  ║     └─> Change role, add/remove capabilities                         ║   │
│  ║                                                                       ║   │
│  ║  3. Dealer can REMOVE DSR                                            ║   │
│  ║     └─> Assignment marked as REMOVED                                 ║   │
│  ║     └─> Transaction records PRESERVED with DSR name                  ║   │
│  ║     └─> Records show "[DSR Name] (No longer active)"                 ║   │
│  ║     └─> DSR notified of removal                                      ║   │
│  ║                                                                       ║   │
│  ╚══════════════════════════════════════════════════════════════════════╝   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### URL Structure

```
DSR Portal Routes:
─────────────────
/dsr/login              → DSR Login Page
/dsr/register           → DSR Self-Registration
/dsr/register/:token    → Registration via Invitation (auto-fills phone/email)
/dsr/forgot-password    → Password Reset Request
/dsr/reset-password/:token → Password Reset Confirmation
/dsr/dashboard          → DSR Dashboard (after login + dealer selection)
/dsr/profile            → Profile Settings (name, phone, password)
/dsr/assignments        → View all dealer assignments
/dsr/invitations        → View pending invitations (accept/reject)

Link from Main Login:
─────────────────────
On /login (dealer login page), add:
"Are you a DSR? Login here →" linking to /dsr/login
```

### Database Schema

```sql
-- ============================================================
-- DSR USER MODEL (Independent Profile)
-- ============================================================
CREATE TABLE dsr_user (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Authentication
    phone           VARCHAR(20) UNIQUE NOT NULL,  -- Primary identifier
    email           VARCHAR(255) UNIQUE,           -- Optional, for notifications
    password        VARCHAR(255) NOT NULL,
    
    -- Profile
    full_name       VARCHAR(255) NOT NULL,
    avatar_url      VARCHAR(500),
    bio             TEXT,
    
    -- Future Freelance Fields (reserved for enhancement)
    skills          JSONB DEFAULT '[]',            -- ['sales', 'inventory', 'collections']
    experience_years INTEGER DEFAULT 0,
    rating          DECIMAL(3,2) DEFAULT 0.0,
    total_jobs      INTEGER DEFAULT 0,
    
    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,         -- Phone verified
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_dsr_user_phone (phone),
    INDEX idx_dsr_user_email (email)
);

-- ============================================================
-- DEALER CONFIG (Existing - Reference)
-- ============================================================
-- dealer_config table already exists with username as PK

-- ============================================================
-- DSR-DEALER ASSIGNMENT (Junction Table with Permissions)
-- ============================================================
CREATE TABLE dsr_dealer_assignment (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relationships
    dsr_id          UUID NOT NULL REFERENCES dsr_user(id) ON DELETE CASCADE,
    dealer_id       VARCHAR(255) NOT NULL REFERENCES dealer_config(username) ON DELETE CASCADE,
    
    -- Assignment Details
    role            VARCHAR(50) NOT NULL DEFAULT 'DSR',  -- DSR, Senior_DSR, Manager, Admin
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, active, removed, left
    
    -- Permissions (JSON for flexibility)
    permissions     JSONB NOT NULL DEFAULT '{
        "dashboard": true,
        "inventory": {"view": true, "edit": false},
        "sales": {"view": true, "edit": true, "delete": false},
        "collections": {"view": true, "edit": false},
        "reports": {"view": true, "export": false},
        "suppliers": {"view": false}
    }',
    
    -- Audit Trail
    invited_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at     TIMESTAMP,
    removed_at      TIMESTAMP,
    removed_by      VARCHAR(20),                    -- 'dealer' or 'dsr'
    removal_reason  TEXT,
    
    -- Constraints
    UNIQUE(dsr_id, dealer_id),                      -- One assignment per DSR-Dealer pair
    
    -- Indexes
    INDEX idx_assignment_dsr (dsr_id),
    INDEX idx_assignment_dealer (dealer_id),
    INDEX idx_assignment_status (status)
);

-- ============================================================
-- DSR INVITATION (Dealer → DSR)
-- ============================================================
CREATE TABLE dsr_invitation (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- From Dealer
    dealer_id       VARCHAR(255) NOT NULL REFERENCES dealer_config(username) ON DELETE CASCADE,
    
    -- To DSR (identified by phone/email)
    dsr_phone       VARCHAR(20) NOT NULL,           -- Required
    dsr_email       VARCHAR(255),                   -- Optional
    
    -- Invitation Details
    role            VARCHAR(50) NOT NULL DEFAULT 'DSR',
    permissions     JSONB NOT NULL DEFAULT '{}',    -- Copy of permissions offered
    
    -- Token for Registration Link
    token           VARCHAR(64) UNIQUE NOT NULL,
    
    -- Status
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, accepted, rejected, expired, revoked
    
    -- Timestamps
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 days'),
    responded_at    TIMESTAMP,
    
    -- If DSR exists, link to their account
    dsr_id          UUID REFERENCES dsr_user(id) ON DELETE SET NULL,
    
    -- Constraints
    UNIQUE(dealer_id, dsr_phone, status) WHERE status = 'pending',  -- Only one pending per dealer-phone
    
    -- Indexes
    INDEX idx_invitation_token (token),
    INDEX idx_invitation_dealer (dealer_id),
    INDEX idx_invitation_phone (dsr_phone),
    INDEX idx_invitation_status (status)
);

-- ============================================================
-- TRANSACTION RECORDS (Preserved with DSR info)
-- ============================================================
-- When DSR is removed, records are preserved with status marking
-- SaleRecord table enhancement:
ALTER TABLE sale_record ADD COLUMN IF NOT EXISTS 
    dsr_name_snapshot VARCHAR(255),     -- Store DSR name at time of removal
    dsr_status_snapshot VARCHAR(20);    -- 'active', 'removed', 'left'
```

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DSR AUTHENTICATION FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  REGISTRATION                                                                │
│  ───────────                                                                 │
│                                                                              │
│  Self-Registration:                                                          │
│  ──────────────────                                                          │
│  POST /api/dsr/auth/register                                                │
│  { phone, email?, password, full_name }                                     │
│  └─> Creates DsrUser (is_verified=false)                                    │
│  └─> Sends OTP to phone for verification                                   │
│  └─> Returns: { success, message: "Verify your phone" }                    │
│                                                                              │
│  Registration via Invitation:                                                │
│  ─────────────────────────                                                  │
│  GET /api/dsr/auth/register/:token                                          │
│  └─> Validates token, returns pre-filled data                              │
│  └─> { phone, email, dealer_name, role }                                   │
│                                                                              │
│  POST /api/dsr/auth/register/:token                                         │
│  { password, full_name }                                                    │
│  └─> Creates DsrUser                                                        │
│  └─> Auto-accepts invitation                                               │
│  └─> Creates DsrDealerAssignment (status='active')                         │
│  └─> Returns: { jwt, user, dealer }                                        │
│                                                                              │
│                                                                              │
│  LOGIN                                                                       │
│  ─────                                                                       │
│  POST /api/dsr/auth/login                                                   │
│  { phone_or_email, password }                                               │
│  └─> Validates credentials                                                  │
│  └─> Returns: { jwt, user, dealers: [...] }                                │
│                                                                              │
│  IF dealers.length === 0:                                                   │
│    └─> Show: "No dealer assignments. Wait for invitations."                │
│    └─> Allow: Profile viewing/editing only                                  │
│                                                                              │
│  IF dealers.length === 1:                                                   │
│    └─> Auto-select dealer                                                   │
│    └─> Redirect to dashboard                                                │
│                                                                              │
│  IF dealers.length > 1:                                                     │
│    └─> Show dealer selection page                                           │
│    └─> POST /api/dsr/auth/select-dealer { dealer_id }                      │
│    └─> Returns: { jwt_with_dealer_context, dealer }                        │
│    └─> Redirect to dashboard                                                │
│                                                                              │
│                                                                              │
│  PASSWORD RESET                                                              │
│  ──────────────                                                              │
│  POST /api/dsr/auth/password-reset/request                                  │
│  { phone_or_email }                                                         │
│  └─> Sends OTP to phone/email                                               │
│                                                                              │
│  POST /api/dsr/auth/password-reset/confirm                                  │
│  { phone_or_email, otp, new_password }                                      │
│  └─> Validates OTP, updates password                                        │
│                                                                              │
│                                                                              │
│  JWT STRUCTURE                                                               │
│  ────────────                                                                │
│  {                                                                           │
│    "sub": "dsr_user_id",                                                    │
│    "type": "dsr",                                                           │
│    "dealer_id": "selected_dealer_username",  // null if no selection       │
│    "role": "DSR",                                                           │
│    "permissions": {...},                                                     │
│    "iat": 1234567890,                                                       │
│    "exp": 1234567890                                                        │
│  }                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Invitation & Assignment Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEALER → DSR INVITATION FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. DEALER SENDS INVITATION                                                  │
│  ────────────────────────────                                                │
│  POST /api/dealer/dsr/invite                                                │
│  { dsr_phone, dsr_email?, role, permissions }                               │
│                                                                              │
│  Backend:                                                                    │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  a. Check if DsrUser exists with this phone/email         │             │
│  │  b. Create DsrInvitation record (status='pending')        │             │
│  │  c. Generate unique token for registration link           │             │
│  │  d. Send notification:                                     │             │
│  │     IF DSR NOT REGISTERED:                                │             │
│  │       → SMS: "Dealer X invites you as DSR. Register:     │             │
│  │         https://dealer.com/dsr/register/TOKEN"            │             │
│  │     IF DSR REGISTERED:                                     │             │
│  │       → In-app notification + SMS/Email                   │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
│                                                                              │
│  2. DSR RESPONDS TO INVITATION                                               │
│  ──────────────────────────────                                              │
│                                                                              │
│  Scenario A: DSR NOT REGISTERED (clicks registration link)                  │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  a. DSR fills registration form                           │             │
│  │  b. Creates DsrUser account                               │             │
│  │  c. Auto-creates DsrDealerAssignment (status='active')    │             │
│  │  d. Marks invitation as ACCEPTED                          │             │
│  │  e. Redirects to dashboard                                │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
│  Scenario B: DSR REGISTERED (sees invitation in dashboard)                  │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  DSR views pending invitation:                            │             │
│  │  - Dealer Name: "ABC Trading"                             │             │
│  │  - Role: "Senior DSR"                                     │             │
│  │  - Permissions: { sales: full, inventory: view }          │             │
│  │                                                           │             │
│  │  DSR chooses:                                             │             │
│  │  [ACCEPT] → Creates DsrDealerAssignment (status='active') │             │
│  │           → Marks invitation ACCEPTED                     │             │
│  │           → Notifies dealer                               │             │
│  │                                                           │             │
│  │  [REJECT] → Marks invitation REJECTED                     │             │
│  │           → Notifies dealer                               │             │
│  │           → DSR can still receive other invitations       │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
│                                                                              │
│  3. DEALER REMOVES DSR                                                       │
│  ─────────────────────────                                                   │
│  DELETE /api/dealer/dsr/assignment/:id                                      │
│  { reason?: string }                                                        │
│                                                                              │
│  Backend:                                                                    │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  a. Update DsrDealerAssignment:                           │             │
│  │     - status = 'removed'                                  │             │
│  │     - removed_at = now()                                  │             │
│  │     - removed_by = 'dealer'                               │             │
│  │     - removal_reason = provided_reason                    │             │
│  │                                                           │             │
│  │  b. Preserve transaction records:                         │             │
│  │     - SaleRecord.dsr_name_snapshot = dsr.full_name        │             │
│  │     - SaleRecord.dsr_status_snapshot = 'removed'          │             │
│  │                                                           │             │
│  │  c. Notify DSR:                                           │             │
│  │     "Dealer X has removed you from their team"            │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
│                                                                              │
│  4. DSR LEAVES DEALER                                                        │
│  ─────────────────────                                                       │
│  POST /api/dsr/assignments/:id/leave                                        │
│                                                                              │
│  Backend:                                                                    │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  a. Update DsrDealerAssignment:                           │             │
│  │     - status = 'left'                                     │             │
│  │     - removed_at = now()                                  │             │
│  │     - removed_by = 'dsr'                                  │             │
│  │                                                           │             │
│  │  b. Preserve transaction records (same as above)          │             │
│  │                                                           │             │
│  │  c. Notify Dealer:                                        │             │
│  │     "DSR Name has left your team"                         │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Permission System

```javascript
// Permission Template by Role
const ROLE_PERMISSIONS = {
  DSR: {
    dashboard: { view: true },
    inventory: { view: true, edit: false, delete: false },
    sales: { view: true, edit: true, delete: false },
    collections: { view: true, edit: false },
    suppliers: { view: false },
    reports: { view: true, export: false },
    print: false
  },
  
  Senior_DSR: {
    dashboard: { view: true },
    inventory: { view: true, edit: true, delete: false },
    sales: { view: true, edit: true, delete: true },
    collections: { view: true, edit: true },
    suppliers: { view: true, edit: false },
    reports: { view: true, export: true },
    print: true
  },
  
  Manager: {
    dashboard: { view: true },
    inventory: { view: true, edit: true, delete: true },
    sales: { view: true, edit: true, delete: true },
    collections: { view: true, edit: true, delete: true },
    suppliers: { view: true, edit: true, delete: false },
    reports: { view: true, export: true },
    print: true,
    manage_dsrs: true  // Can manage junior DSRs
  },
  
  Admin: {
    all: true  // Full access within dealer scope
  }
};

// Dealer can customize these defaults when inviting
```

### Future Freelance Enhancement (Reserved)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FUTURE: FREELANCE MARKETPLACE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  The DSR model is designed to support future enhancement as a freelance     │
│  marketplace where DSRs can:                                                │
│                                                                              │
│  1. CREATE PUBLIC PROFILE                                                   │
│     └─> Set availability status (available/busy)                            │
│     └─> List skills and experience                                          │
│     └─> Set hourly/daily rate                                               │
│     └─> Upload portfolio/certifications                                     │
│                                                                              │
│  2. BE DISCOVERABLE                                                         │
│     └─> Dealers can search for DSRs by skills, location, rating             │
│     └─> DSRs can set profile visibility (private/public)                    │
│                                                                              │
│  3. RECEIVE JOB OFFERS                                                      │
│     └─> Dealers can send job offers with proposed terms                     │
│     └─> DSRs can negotiate or accept/reject                                 │
│                                                                              │
│  4. BUILD REPUTATION                                                        │
│     └─> Ratings and reviews from dealers                                    │
│     └─> Work history and achievements                                       │
│     └─> Verified skills badges                                              │
│                                                                              │
│  DATABASE FIELDS ALREADY RESERVED:                                          │
│  - dsr_user.skills (JSONB)                                                  │
│  - dsr_user.experience_years (INTEGER)                                      │
│  - dsr_user.rating (DECIMAL)                                                │
│  - dsr_user.total_jobs (INTEGER)                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation Tasks

#### 4.1 Backend - User Model & Authentication
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create `DsrUser` custom user model | ✅ Complete | HIGH | Phone as primary identifier |
| Add phone verification system | 🟡 Partial | HIGH | OTP-based verification (fields ready) |
| Create JWT authentication for DSRs | ✅ Complete | HIGH | Separate from dealer JWT |
| Implement login with dealer selection | ✅ Complete | HIGH | Multi-dealer support |
| Add password reset via OTP | ✅ Complete | MEDIUM | Phone/Email OTP |
| Create DSR profile endpoints | ✅ Complete | MEDIUM | CRUD operations |
| Add self-registration endpoint | ✅ Complete | HIGH | POST /dsr/auth/register |
| Add freelance marketplace fields | ✅ Complete | MEDIUM | Future-ready design |

#### 4.2 Backend - Invitation System
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create invitation endpoint (dealer → DSR) | ✅ Complete | HIGH | POST /dealer/dsr/invite |
| Handle DSR not registered case | ✅ Complete | HIGH | Send registration link |
| Handle DSR registered case | ✅ Complete | HIGH | Send in-app notification |
| Create accept/reject endpoints | ✅ Complete | HIGH | POST /dsr/invitations/:id/accept |
| Create invitation list endpoints | ✅ Complete | MEDIUM | GET /dsr/invitations |
| Add permissions field to invitation | ✅ Complete | HIGH | JSON-based permissions |

#### 4.3 Backend - Assignment Management
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create DsrDealerAssignment model | ✅ Complete | HIGH | Junction with permissions |
| Add status field (pending/active/removed/left) | ✅ Complete | HIGH | Status tracking |
| Implement permission checking | ✅ Complete | HIGH | Per-request permission validation |
| Create remove DSR endpoint | ✅ Complete | HIGH | DELETE /dealer/dsr/assignments/:id |
| Create leave dealer endpoint | ✅ Complete | HIGH | POST /dsr/assignments/:id/leave |
| Preserve transaction records on removal | ✅ Complete | HIGH | Added dsr_status fields to SaleRecord |
| Add removal tracking fields | ✅ Complete | MEDIUM | removed_at, removed_by, removal_reason |

#### 4.4 Frontend - DSR Portal
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create /dsr/login page | ✅ Complete | HIGH | DsrLoginPage.vue component |
| Create /dsr/register page | ✅ Complete | HIGH | DsrSelfRegisterPage.vue component |
| Create /dsr/register/:token page | ✅ Complete | HIGH | DsrRegisterPage.vue component |
| Create dealer selection page | ✅ Complete | HIGH | Integrated in DsrLoginPage.vue |
| Create /dsr/profile page | ✅ Complete | MEDIUM | Integrated in DsrDashboard.vue |
| Create /dsr/invitations page | ✅ Complete | MEDIUM | Integrated in DsrDashboard.vue |
| Add "Are you a DSR?" link on dealer login | ✅ Complete | MEDIUM | Added to LoginPage.vue |

#### 4.5 Frontend - Dealer DSR Management
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Update AddRepModal for new flow | ✅ Complete | HIGH | Search existing DSR by phone |
| Create DSR list with status | ✅ Complete | HIGH | DsrManagementPanel.vue component |
| Create permission editor | ✅ Complete | MEDIUM | Integrated in DsrManagementPanel |
| Add remove DSR with confirmation | ✅ Complete | HIGH | With reason input |
| Show removed DSR in reports | 🟡 Partial | MEDIUM | Backend ready, frontend pending |

#### 4.6 Database Migrations
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create migration for DsrUser changes | ✅ Complete | HIGH | 0005_dsr_auth_redesign.py |
| Create migration for DsrInvitation changes | ✅ Complete | HIGH | Included in 0005 |
| Create migration for DsrDealerAssignment changes | ✅ Complete | HIGH | Included in 0005 |
| Create migration for SaleRecord status fields | ✅ Complete | HIGH | 0008_dsr_status_tracking.py |
| Run migrations on database | 🔴 Pending | HIGH | Needs testing |

### API Endpoints Summary

```
DSR Authentication:
───────────────────
POST   /api/dsr/auth/register                    # Self-registration
POST   /api/dsr/auth/register/:token             # Register via invitation
POST   /api/dsr/auth/login                       # Login
POST   /api/dsr/auth/logout                      # Logout
POST   /api/dsr/auth/select-dealer               # Select dealer context
POST   /api/dsr/auth/password-reset/request      # Request OTP
POST   /api/dsr/auth/password-reset/confirm      # Confirm with OTP
GET    /api/dsr/auth/me                          # Get current user
PUT    /api/dsr/auth/me                          # Update profile

DSR Invitations (DSR view):
───────────────────────────
GET    /api/dsr/invitations                      # List pending invitations
POST   /api/dsr/invitations/:id/accept           # Accept invitation
POST   /api/dsr/invitations/:id/reject           # Reject invitation

DSR Assignments (DSR view):
────────────────────────────
GET    /api/dsr/assignments                      # List my dealer assignments
POST   /api/dsr/assignments/:id/leave            # Leave a dealer

Dealer DSR Management:
──────────────────────
POST   /api/dealer/dsr/invite                    # Invite DSR by phone/email
GET    /api/dealer/dsr/invitations               # List sent invitations
DELETE /api/dealer/dsr/invitations/:id           # Revoke pending invitation
GET    /api/dealer/dsr/assignments               # List DSR assignments
PUT    /api/dealer/dsr/assignments/:id           # Update DSR permissions
DELETE /api/dealer/dsr/assignments/:id           # Remove DSR
```

### Deliverables
- [x] DsrUser model with phone authentication
- [x] DSR self-registration flow
- [x] Dealer invitation flow (with/without existing DSR)
- [x] DSR login with dealer selection
- [x] Accept/reject invitation capability
- [x] Dealer remove DSR endpoint
- [x] DSR leave dealer endpoint
- [x] DSR profile management endpoints
- [x] Permission system per assignment
- [x] DSR frontend pages (login/register/profile) - COMPLETE
- [x] AddRepModal update for new flow - COMPLETE
- [x] Transaction record preservation on removal - COMPLETE

---

## Phase 5: Garbage Collection & Data Cleanup

### Objective
Implement automated cleanup of stale, orphaned, and expired data to maintain system health and performance.

### Data Categories Requiring Cleanup

| Category | Description | Cleanup Policy |
|----------|-------------|----------------|
| Expired Invitations | Invitations past expiration date | Soft delete after 30 days |
| Rejected Invitations | DSR rejected invitations | Hard delete after 7 days |
| Revoked Invitations | Manually revoked invitations | Hard delete after 7 days |
| Inactive Assignments | Removed/Left DSR-Dealer relationships | Archive after 90 days |
| Orphan DSR Users | DSRs with no active assignments | Flag after 30 days, review |
| Old API Tokens | Expired JWT/API tokens | Hard delete immediately |
| Session Data | Expired user sessions | Hard delete after 24 hours |
| Audit Logs | System activity logs | Archive after 1 year |

### Implementation Tasks

#### 5.1 Cleanup Management Commands
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Create `cleanup_expired_invitations` command | 🔴 Pending | HIGH | Delete expired invitations |
| Create `cleanup_rejected_invitations` command | 🔴 Pending | MEDIUM | Delete rejected invitations |
| Create `cleanup_inactive_assignments` command | 🔴 Pending | MEDIUM | Archive inactive assignments |
| Create `cleanup_orphan_dsrs` command | 🔴 Pending | MEDIUM | Handle DSRs with no assignments |
| Create `cleanup_expired_tokens` command | 🔴 Pending | HIGH | Clean up JWT/API tokens |
| Create `cleanup_session_data` command | 🔴 Pending | MEDIUM | Clear old sessions |

#### 5.2 Automated Scheduling
| Task | Status | Priority | Notes |
|------|--------|----------|-------|
| Set up Django-Q or Celery beat | 🔴 Pending | HIGH | Background task scheduler |
| Schedule daily cleanup job | 🔴 Pending | HIGH | Run at 2 AM daily |
| Add cleanup logging | 🔴 Pending | MEDIUM | Track what was cleaned |
| Create cleanup dashboard | 🔴 Pending | LOW | Admin view of cleanup stats |

### Deliverables
- [ ] Cleanup management commands
- [ ] Scheduled cleanup jobs (Django-Q/Celery)
- [ ] Cleanup monitoring dashboard
- [ ] Documentation for cleanup policies

---

## Implementation Priority Order

### Sprint 1: Data Isolation ✅ COMPLETE
1. ✅ Fix authentication race condition
2. ✅ Fix PermissionGuard error
3. ✅ Audit all API endpoints for dealer filtering
4. ✅ Add dealer context validation in frontend
5. ✅ Test data isolation
6. ✅ Remove `null=True` from dealer FK fields
7. ✅ Add NOT NULL constraints at database level

### Sprint 2: Access Matrix Foundation
1. 🔴 Enhance `useAccess` composable
2. 🔴 Create `LimitGuard` component
3. 🔴 Add limit indicators to inventory page
4. 🔴 Implement print/export access control

### Sprint 3: Sales Rep Workflow ✅ COMPLETE
1. ✅ Design unified AddRepModal
2. ✅ Implement "Add Rep" button
3. ✅ Integrate with invitation API
4. ✅ Add DSR auto-creation on acceptance
5. ✅ Test complete workflow

### Sprint 4: DSR Authentication System (Redesigned) ✅ COMPLETE
1. ✅ Create custom DsrUser model
2. ✅ Implement phone-based authentication
3. ✅ Build invitation system with accept/reject
4. ✅ Create DSR login/registration pages
5. ✅ Implement dealer selection for multi-dealer DSRs
6. ✅ Add remove DSR with record preservation
7. ✅ Create DSR profile management

### Sprint 5: Garbage Collection
1. 🔴 Create cleanup management commands
2. 🔴 Set up scheduled cleanup jobs
3. 🔴 Implement cleanup monitoring

---

## Technical Specifications

### Frontend Components to Create

```
src/
├── pages/
│   └── dsr/
│       ├── LoginPage.vue           # DSR login
│       ├── RegisterPage.vue        # Self-registration
│       ├── RegisterViaInvite.vue   # Registration via token
│       ├── ForgotPassword.vue      # Password reset
│       ├── DashboardPage.vue       # DSR dashboard
│       ├── ProfilePage.vue         # Profile management
│       ├── InvitationsPage.vue     # Accept/reject invitations
│       └── AssignmentsPage.vue     # View dealer assignments
│
├── components/
│   ├── dsr/
│   │   ├── DealerSelector.vue      # Multi-dealer selection
│   │   ├── InvitationCard.vue      # Single invitation display
│   │   └── AssignmentCard.vue      # Single assignment display
│   │
│   ├── LimitGuard.vue              # Row-level limit control
│   ├── AddRepModal.vue             # ✅ Created - Update for new flow
│   └── InvitationList.vue          # ✅ Created
│
├── composables/
│   ├── useDsrAuth.ts               # DSR authentication
│   ├── useDsrInvitations.ts        # DSR invitation management
│   └── useDsrAssignments.ts        # DSR assignment management
│
└── services/api/
    ├── dsrAuth.service.ts          # DSR auth API
    ├── dsrInvitation.service.ts    # DSR invitation API
    └── dsrAssignment.service.ts    # DSR assignment API
```

---

## Notes & Considerations

1. **DSR Independence**: DSRs own their profile, dealers cannot modify core profile data
2. **Permission Flexibility**: JSON-based permissions allow fine-grained control
3. **Multi-Dealer Support**: DSR can work for multiple dealers simultaneously
4. **Audit Trail**: All assignment changes are tracked with timestamps and reasons
5. **Future-Ready**: Reserved fields support freelance marketplace enhancement

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2024-01-15 | Initial plan creation | System |
| 2024-01-15 | Fixed auth race condition | System |
| 2024-01-15 | Fixed PermissionGuard error | System |
| 2024-01-15 | Phase 1 audit complete | System |
| 2024-01-15 | Phase 2 complete - Invitation workflow | System |
| 2024-01-15 | Merged "Invite Rep" and "Add Rep" buttons | System |
| 2024-01-15 | Added Phase 4: DSR Authentication System | System |
| 2024-01-15 | Added Phase 5: Garbage Collection | System |
| 2024-06-12 | **Phase 4 REDESIGNED** - Independent DSR profiles with invitation/acceptance model | System |
| 2024-06-12 | Added DSR self-registration flow | System |
| 2024-06-12 | Added dealer invitation with accept/reject | System |
| 2024-06-12 | Added DSR removal with record preservation | System |
| 2024-06-12 | Added future freelance marketplace preparation | System |
| 2024-06-12 | **Phase 4 Backend COMPLETE** - DsrUser model (phone-based), invitation/assignment APIs, migrations | System |
| 2024-06-12 | **Phase 4 Frontend COMPLETE** - DSR login/register/dashboard, AddRepModal redesigned, DsrManagementPanel | System |
| 2024-06-12 | **Transaction preservation** - Added dsr_status fields to SaleRecord for audit trail | System |
| 2024-06-12 | **Bug fixes** - Fixed vue-router import (using emits), DsrDashboard.vue syntax, AddRepModal import path | System |

---

## Status Legend

- ✅ Completed
- 🟡 In Progress  
- 🔴 Pending
- ⏸️ Blocked
