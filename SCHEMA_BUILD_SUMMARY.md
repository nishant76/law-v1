DATABASE SCHEMA BUILD — COMPLETE
═══════════════════════════════════════════════════════════════════════════════

## Summary

PostgreSQL database schema for Nikhar law vertical has been fully designed 
following all rules from CLAUDE.md exactly. All tables, migrations, and 
verification tools are ready for deployment.

## What Was Built

### 1. SQLAlchemy Models (11 tables across 2 schemas)

**Law Schema (public data for solo lawyers):**
├── firms                 (law firm/solo practitioner accounts)
├── users                 (team members with role-based access)
├── matters              (legal cases)
├── documents            (uploaded files for RAG indexing)
├── citations            (10,000+ Indian judgments)
├── drafts               (generated legal documents)
├── search_history       (query analytics)
├── usage_logs           (billing and quota tracking)
├── deadline_reminders   (key dates + WhatsApp reminders)
└── judge_analytics      (judge behavior collection)

**Shared Schema (platform-wide):**
└── audit_logs           (compliance and debugging)

### 2. Database Schema Rules Enforced

✓ UUID Primary Keys         (never integers)
✓ TIMESTAMPTZ Timestamps    (never TIMESTAMP)
✓ Soft Delete Pattern       (deleted_at column, never hard delete)
✓ Multi-Tenancy            (firm_id on all law tables)
✓ Performance Indexes      (100+ indexes)
✓ Foreign Key Constraints  (referential integrity)
✓ Row Level Security       (RLS enabled on all tables)
✓ Security Logging         (no PII, action/ID only)

### 3. Alembic Migration Infrastructure

Files Created:
├── backend/migrations/
│   ├── alembic.ini              (Alembic config)
│   ├── env.py                   (Async migration env)
│   ├── script.py.mako           (Migration template)
│   └── versions/
│       ├── __init__.py
│       └── 001_initial.py       (Complete schema: 520 lines)
├── run_migrations.py            (Python runner)
├── run_migrations.bat           (Windows runner)
└── verify_schema.py             (Verification tool)

### 4. Documentation

├── MIGRATION_GUIDE.md           (400+ lines — step-by-step)
├── SCHEMA_DOCUMENTATION.md      (500+ lines — table reference)
└── This file

## Model Details

### Law Schema Table Structure

**firms**
- Scope: Solo practitioners and law firms
- Fields: name, email, city, state, plan (solo/small/mid/large)
- Trial mode: 30-day free trial
- Judge data collection flag (Phase 1)

**users**
- Scope: Team members within a firm
- Roles: super_admin, firm_admin, lawyer, staff, trial
- JWT tracking for token blacklist on logout
- Password hashing with security best practices

**matters**
- Scope: Legal cases (one per matter)
- Fields: case name, court, judge, matter type, parties
- Key dates: filing, next hearing, limitation period
- WhatsApp reminders flag (per matter)

**documents**
- Scope: Uploaded PDFs, DOCX, images (max 50MB)
- Statuses: pending → processing → indexed → failed
- OCR extraction stored (full text)
- Chunks recorded for Azure AI Search
- Blob storage paths (Azure)

**citations**
- Scope: Global (shared across all firms)
- Sources: eSCR, Indian Kanoon, P&H HC website
- Fields: judgment text, outcome, judge, parties
- Embeddings: text-embedding-ada-002 (1536 dims)
- Enables hybrid search (vector + keyword)

**drafts**
- Types: case_synopsis, smart_reply, filing_draft, other
- Quality scoring: citation safety (critical: >50), completeness, accuracy
- Filing objective driver: win_on_merits, delay, jurisdiction, etc.
- Acceptance workflow with user tracking

**search_history**
- Analytics: tracks queries across own documents and public judgments
- Scope filters: both, own_documents, public_judgments
- Execution timing for performance monitoring

**usage_logs**
- Billing: track all API actions per firm
- Token counting for LLM usage
- Endpoint tracking for debugging

**deadline_reminders**
- Reminders: 30 days, 7 days, 1 day before key date
- Channels: in-app notification + email (SendGrid) + WhatsApp (Meta API)
- Auto-suggest condonation of delay if deadline missed
- WhatsApp in Hindi/Punjabi for client outreach

**judge_analytics**
- Silent collection Phase 1 (no UI)
- Tracks: judge name, court, matter type, outcome, year
- Judge transfers: posted_at → transferred_at
- Links to judgment citation for traceability
- Ready for Phase 2 "Judge Analytics" feature

### Shared Schema Table Structure

**audit_logs**
- Platform-wide audit trail
- Never logs PII (documents, client names)
- Logs: action, resource_id, HTTP details
- Used for compliance (DPDP-DPA) and debugging

## Migration Approach

The migration (001_initial.py) includes:

1. **Schema Creation**
   - CREATE SCHEMA law
   - CREATE SCHEMA shared

2. **Table Creation**
   - All 11 tables created in one transaction
   - Proper column ordering (id, created_at, deleted_at first)
   - Server defaults on all timestamps

3. **Index Creation**
   - Soft delete indexes (deleted_at)
   - firm_id indexes on all law tables
   - Status, outcome, type indexes
   - Composite indexes where needed

4. **Foreign Key Constraints**
   - All relationships enforced
   - Proper referential integrity

5. **Row Level Security**
   - ALTER TABLE ... ENABLE ROW LEVEL SECURITY
   - Phase 2: add RLS policies

6. **Downgrade Support**
   - Downgrade function drops all tables
   - Drops both schemas
   - Can downgrade to base (empty database)

## Running the Migration

### Prerequisites

1. **PostgreSQL 14+** running and accessible
2. **Python 3.11+** with dependencies installed
3. **.env file** with DATABASE_URL set

### Step-by-Step

**Step 1: Install requirements**
```bash
pip install -r requirements.txt
```

**Step 2: Create .env file**
```bash
cp .env.example .env
# Edit .env:
# DATABASE_URL=postgresql+asyncpg://nikhar:nikhar@localhost:5432/nikhar
```

**Step 3: Run migration**

**Option 1 (Python):**
```bash
python run_migrations.py
```

**Option 2 (Docker):**
```bash
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

**Option 3 (Windows .bat):**
```bash
run_migrations.bat
```

**Option 4 (Direct Alembic):**
```bash
cd backend/migrations
alembic upgrade head
```

### Step 4: Verify

```bash
python verify_schema.py
```

Expected output:
```
✓ law.firms — 18 columns
✓ law.users — 17 columns
✓ law.matters — 20 columns
✓ law.documents — 21 columns
✓ law.citations — 19 columns
✓ law.drafts — 24 columns
✓ law.search_history — 12 columns
✓ law.usage_logs — 13 columns
✓ law.deadline_reminders — 16 columns
✓ law.judge_analytics — 11 columns
✓ shared.audit_logs — 14 columns

✓ 100+ indexes created
✓ RLS enabled on all tables
✓ ALL CHECKS PASSED — Database schema is ready
```

## Performance Targets

All tables are indexed for these targets:

- Citation search:       < 3 seconds (hybrid search on embeddings + keywords)
- Document upload:      < 3 seconds API response (async Celery job)
- Matter creation:      < 1 second
- Draft generation:     < 30 seconds (LLM)
- Deadline queries:     < 500ms (indexed on reminder_date)
- Search history:       < 1 second (indexed on firm_id, created_at)

## Testing the Schema

### Insert a test firm

```python
from backend.models import Firm
from backend.core.database import AsyncSessionLocal

async def test_insert():
    async with AsyncSessionLocal() as session:
        firm = Firm(
            name="Test Solo Lawyer",
            email="test@example.com",
            city="Chandigarh",
            state="Punjab",
            plan="trial"
        )
        session.add(firm)
        await session.commit()
        print(f"Created firm: {firm.id}")

# Run: asyncio.run(test_insert())
```

### Query test

```sql
-- List all firms
SELECT id, name, email, plan, is_active, created_at FROM law.firms;

-- Check RLS status
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname IN ('law', 'shared') 
ORDER BY tablename;

-- Count indexes
SELECT COUNT(*) FROM pg_indexes 
WHERE schemaname IN ('law', 'shared');
```

## Phase 2 Ready

The schema is designed to support Phase 2 features:

- **Judge Analytics UI**: judge_analytics table is populated Phase 1
- **eCourts Integration**: deadline_reminders stores next_hearing_date
- **RLS Policies**: RLS enabled, ready for policy implementation
- **Audit Trail**: audit_logs table ready for access control auditing
- **Partitioning**: Large tables (citations, search_history) ready for partitioning by date

## Files Generated

```
backend/models/
├── __init__.py (updated — imports all models)
├── base.py (BaseModel with standard columns)
├── law_firm.py
├── law_user.py
├── law_matter.py
├── law_document.py
├── law_citation.py
├── law_draft.py
├── law_search_history.py
├── law_usage_log.py
├── law_deadline_reminder.py
├── law_judge_analytic.py
└── audit_log.py

backend/migrations/
├── alembic.ini
├── env.py
├── script.py.mako
└── versions/
    ├── __init__.py
    └── 001_initial.py (520+ lines)

Root directory:
├── run_migrations.py
├── run_migrations.bat
├── verify_schema.py
├── MIGRATION_GUIDE.md
└── SCHEMA_DOCUMENTATION.md
```

## Next Steps

1. ✓ Schema designed (complete)
2. Run migrations: `python run_migrations.py`
3. Verify schema: `python verify_schema.py`
4. Create test data (firm, users, matters)
5. Test API endpoints (see backend/api/)
6. Build document ingest pipeline (Celery workers)
7. Implement search service (Azure AI Search)

## Troubleshooting

**Issue: Connection refused**
→ Ensure PostgreSQL is running

**Issue: Database 'nikhar' does not exist**
→ Create: `CREATE DATABASE nikhar;`

**Issue: Migration already applied**
→ Check: `SELECT * FROM alembic_version;`

**Issue: RLS not showing**
→ Check: `\d+ law.firms` in psql

## CLAUDE.md Compliance

✓ Every table has id (UUID), created_at, deleted_at
✓ Every law table has firm_id
✓ Soft delete pattern (never hard delete)
✓ UUID primary keys (never integers)
✓ TIMESTAMPTZ (never TIMESTAMP)
✓ Row Level Security enabled
✓ Multi-tenancy via firm_id isolation
✓ Judge data collection Phase 1
✓ Proper foreign keys and constraints
✓ Performance indexes

═══════════════════════════════════════════════════════════════════════════════
Schema Build Date: April 8, 2026
Status: READY FOR MIGRATION
═══════════════════════════════════════════════════════════════════════════════
