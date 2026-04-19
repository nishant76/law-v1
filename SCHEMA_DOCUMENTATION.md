# PostgreSQL Schema Documentation

## Complete Table Structure

### Law Schema (law.*)

#### 1. firms
Represents law firm or solo practitioner accounts.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         — NOT APPLICABLE (this IS the firm)
name            VARCHAR(255) NOT NULL
email           VARCHAR(255) UNIQUE NOT NULL
phone           VARCHAR(20)
city            VARCHAR(100)  — e.g., "Chandigarh", "Ludhiana"
state           VARCHAR(100)  — e.g., "Punjab", "Haryana"
plan            VARCHAR(50) DEFAULT 'trial'  — solo, small, mid, large, trial
trial_days      INTEGER DEFAULT 30
trial_started_at TIMESTAMPTZ
is_active       BOOLEAN DEFAULT true
collect_judge_data BOOLEAN DEFAULT true  — Phase 1 collection
updated_at      TIMESTAMPTZ
```

#### 2. users
Team members — lawyers, staff, admins.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL FK → firms.id
name            VARCHAR(255) NOT NULL
email           VARCHAR(255) UNIQUE NOT NULL
phone           VARCHAR(20)
password_hash   VARCHAR(255) NOT NULL
role            ENUM (super_admin, firm_admin, lawyer, staff, trial)
is_active       BOOLEAN DEFAULT true
last_token_issued_at TIMESTAMPTZ  — JWT blacklist tracking
updated_at      TIMESTAMPTZ
last_login_at   TIMESTAMPTZ
```

#### 3. matters
Legal cases and matters.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL FK → firms.id
matter_number   VARCHAR(100)  — e.g., "SLP-2026-001"
case_name       VARCHAR(500) NOT NULL
court           VARCHAR(255)  — e.g., "District Court, Amritsar"
judge_name      VARCHAR(255)
matter_type     VARCHAR(100)  — civil, criminal, consumer, cheque_bounce, etc.
petitioner      VARCHAR(500)
respondent      VARCHAR(500)
filing_date     TIMESTAMPTZ
next_hearing_date TIMESTAMPTZ
limitation_date TIMESTAMPTZ  — For deadline tracking
description     TEXT
is_active       BOOLEAN DEFAULT true
client_name     VARCHAR(255)
client_phone    VARCHAR(20)
whatsapp_reminders_enabled BOOLEAN DEFAULT false
updated_at      TIMESTAMPTZ
```

#### 4. documents
Uploaded case files for RAG indexing.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL FK → firms.id
matter_id       UUID FK → matters.id (NULLABLE)
file_name       VARCHAR(500) NOT NULL
file_type       VARCHAR(50)  — pdf, docx, image, etc.
file_size_bytes INTEGER NOT NULL
blob_path       VARCHAR(500) NOT NULL  — Path in Azure Blob Storage
blob_url        VARCHAR(500)  — Signed URL for retrieval
status          ENUM (pending, processing, indexed, failed)
error_reason    TEXT  — Plain English error message
ocr_text        TEXT  — Full extracted text
chunk_count     INTEGER DEFAULT 0  — Number of chunks in Azure AI Search
search_index_name VARCHAR(100) DEFAULT 'law-documents'
uploaded_by_user_id UUID FK → users.id (NULLABLE)
upload_source   VARCHAR(50) DEFAULT 'web'  — web, google_drive
updated_at      TIMESTAMPTZ
indexed_at      TIMESTAMPTZ
```

#### 5. citations
Indian law judgments from public sources.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
citation_key    VARCHAR(100) UNIQUE NOT NULL  — e.g., "2024-SCC-1"
case_name       VARCHAR(500) NOT NULL
court           VARCHAR(255) NOT NULL INDEXED  — Supreme, High, District
year            INTEGER NOT NULL INDEXED
petitioner      VARCHAR(500)
respondent      VARCHAR(500)
judge_name      VARCHAR(255)
judgment_date   TIMESTAMPTZ
judgment_text   TEXT
summary         TEXT  — Editorial summary
matter_type     VARCHAR(100) INDEXED  — civil, criminal, etc.
outcome         VARCHAR(50)  — granted, refused, allowed, dismissed, bail_granted
official_source VARCHAR(100) NOT NULL  — eSCR, P&H HC, Punjab district court portals
source_url      VARCHAR(500)
embedding_vector VARCHAR(10000)  — 1536-dim vector as JSON
updated_at      TIMESTAMPTZ
scraped_at      TIMESTAMPTZ
```

NOTES:
- `citation_key` is globally unique across all firms
- `embedding_vector` stores text-embedding-ada-002 embeddings (1536 dimensions)
- Used for hybrid search (vector + keyword)
- Public data (no firm_id) — visible to all firms

#### 6. drafts
Generated legal documents.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL FK → firms.id
matter_id       UUID FK → matters.id (NULLABLE)
draft_type      ENUM (case_synopsis, smart_reply, filing_draft, other)
status          ENUM (generating, generated, accepted, rejected)
title           VARCHAR(500)
content         TEXT NOT NULL
quality_score   INTEGER (0-100)
citation_safety_score INTEGER (0-100)  — Critical: block if < 50
completeness_score INTEGER (0-100)
legal_accuracy_score INTEGER (0-100)
language_score  INTEGER (0-100)
generated_by_user_id UUID FK → users.id
filing_objective VARCHAR(100)  — win_on_merits, delay, jurisdiction, settlement, appeal
accepted_by_user_id UUID FK → users.id
accepted_at     TIMESTAMPTZ
exported_format VARCHAR(50)  — docx, pdf
updated_at      TIMESTAMPTZ
```

#### 7. search_history
Search query analytics.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL FK → firms.id
user_id         UUID FK → users.id (NULLABLE)
query           TEXT NOT NULL
search_scope    VARCHAR(100) DEFAULT 'both'  — both, own_documents, public_judgments
results_from_own_documents INTEGER DEFAULT 0
results_from_public_judgments INTEGER DEFAULT 0
execution_time_ms INTEGER  — Query performance tracking
search_filters  TEXT  — JSON: outcome filter, court, etc.
updated_at      TIMESTAMPTZ
```

#### 8. usage_logs
API usage tracking for billing and quotas.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL FK → firms.id
user_id         UUID FK → users.id (NULLABLE)
action          VARCHAR(100) NOT NULL INDEXED  — document_upload, search, draft_generate
resource_id     UUID  — document_id, draft_id, matter_id
resource_type   VARCHAR(100)  — document, draft, search
tokens_used     INTEGER DEFAULT 0  — For LLM calls
endpoint        VARCHAR(500)
request_id      VARCHAR(100)  — Correlation ID
updated_at      TIMESTAMPTZ
```

#### 9. deadline_reminders
Key dates and notification tracking.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL FK → firms.id
matter_id       UUID NOT NULL FK → matters.id
reminder_type   ENUM (hearing, filing_deadline, limitation_period, urgent)
title           VARCHAR(255) NOT NULL
description     VARCHAR(1000)
key_date        TIMESTAMPTZ NOT NULL  — The actual deadline
reminder_date   TIMESTAMPTZ NOT NULL INDEXED  — When to send reminder
status          ENUM (pending, sent, missed) DEFAULT 'pending'
email_sent      BOOLEAN DEFAULT false
whatsapp_sent   BOOLEAN DEFAULT false
whatsapp_message_template VARCHAR(1000)  — Message to client in Hindi/Punjabi
sent_at         TIMESTAMPTZ
missed_at       TIMESTAMPTZ  — If deadline missed, auto-suggest condonation
updated_at      TIMESTAMPTZ
```

REMINDERS LOGIC:
- If key_date > 30 days: set reminder_date to NOW + (key_date - 30d)
- Celery cron checks daily: send reminders where reminder_date >= NOW
- Channels: in-app notification + email + WhatsApp (if enabled)

#### 10. judge_analytics
Judge behavior data (Phase 1 collection, Phase 2 analysis feature).

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         N/A (shared data across all firms)
judge_name      VARCHAR(255) NOT NULL INDEXED
court           VARCHAR(255) NOT NULL INDEXED  — Current posting
matter_type     VARCHAR(100) INDEXED  — civil, criminal, etc.
outcome         VARCHAR(50) INDEXED  — granted, refused, allowed, dismissed
citation_id     UUID FK → citations.id  — Links to judgment source
year            INTEGER NOT NULL INDEXED
posted_at       TIMESTAMPTZ  — When posted to court
transferred_at  TIMESTAMPTZ  — When transferred elsewhere
updated_at      TIMESTAMPTZ
```

NOTES:
- No firm_id (global analytics)
- Records every judgment by every judge
- Tracks judge transfers (posted_at → transferred_at)
- Phase 2: enable "Judge Analytics" feature with stats

### Shared Schema (shared.*)

#### 11. audit_logs
Platform-wide audit trail.

```
id              UUID PRIMARY KEY
created_at      TIMESTAMPTZ NOT NULL
deleted_at      TIMESTAMPTZ (soft delete)
firm_id         UUID NOT NULL INDEXED
user_id         UUID INDEXED
action          VARCHAR(100) NOT NULL INDEXED  — login, create_document, generate_draft
resource_type   VARCHAR(100)  — document, draft, matter, user, firm
resource_id     UUID
details         TEXT  — JSON with action-specific data
request_id      VARCHAR(100)  — HTTP correlation ID
endpoint        VARCHAR(500)  — API endpoint path
http_method     VARCHAR(10)  — GET, POST, PUT, DELETE
status_code     INTEGER  — HTTP response code
ip_address      VARCHAR(50)
```

RULES:
- Never log PII (no document content, client names)
- Log only actions and IDs
- Used for compliance and debugging

---

## Key Rules Enforced

### ✓ Every table has:
- `id` UUID PRIMARY KEY with DEFAULT gen_random_uuid()
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `deleted_at` TIMESTAMPTZ nullable (soft delete)

### ✓ Law schema tables have:
- `firm_id` UUID NOT NULL (multi-tenancy)

### ✓ Indexes:
- Soft delete index on `deleted_at`
- firm_id index on all law tables
- Outcome, matter_type, year indexes on citations
- Status indexes on documents, drafts
- reminder_date index on deadline_reminders

### ✓ Foreign Keys:
- All relationships properly constrained
- No orphaned data possible

### ✓ Row Level Security:
- RLS enabled on all tables via `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- Phase 2: add RLS policies

### ✓ Soft Deletes:
- Never hard delete
- Queries filter `WHERE deleted_at IS NULL`

---

## Performance Targets

- Citation search: < 3 seconds (hybrid search)
- Document upload: < 3 seconds API response (async background job)
- Matter creation: < 1 second
- Draft generation: < 30 seconds
- Search history queries: indexed on firm_id and created_at
- Deadline reminder queries: indexed on reminder_date

---

## Migration Path

**Current:** Initial schema created via Alembic migration 001_initial

**Phases:**
- Phase 1: Basic schema (now complete)
- Phase 2: Add RLS policies, judge analytics UI, eCourts integration
- Phase 3: Partitioning for scale (100M+ judgments)

---

## Connection Example

```python
from backend.core.database import AsyncSessionLocal
from backend.models import Firm, User, Matter
from sqlalchemy import select

async def create_firm():
    async with AsyncSessionLocal() as session:
        firm = Firm(
            name="Solo Lawyer LLC",
            email="lawyer@example.com",
            city="Chandigarh",
            state="Punjab",
            plan="solo"
        )
        session.add(firm)
        await session.commit()
        print(f"Created firm: {firm.id}")

# Run: asyncio.run(create_firm())
```

---

## References

- CLAUDE.md: Detailed requirements
- MIGRATION_GUIDE.md: How to run migrations
- run_migrations.py: Migration runner
- verify_schema.py: Schema verification tool
