# Database Migration Guide

## Overview

This document explains how to run the PostgreSQL migrations for the Nikhar platform.

All tables follow the rules from CLAUDE.md:
- ✓ UUID primary keys (never integers)
- ✓ `created_at`, `deleted_at` columns (TIMESTAMPTZ)
- ✓ Soft deletes only (never hard delete)
- ✓ `firm_id` on all law schema tables
- ✓ Row Level Security (RLS) enabled
- ✓ Proper indexes for performance

## Schema Overview

### law schema (10 tables)
- `firms` — law firm or solo practitioner accounts
- `users` — team members (lawyers, staff, admins)
- `matters` — legal cases
- `documents` — uploaded case files for RAG
- `citations` — Indian law judgments database (10,000+ public judgments)
- `drafts` — generated legal documents
- `search_history` — search analytics
- `usage_logs` — API usage tracking for billing
- `deadline_reminders` — key dates and notification tracking
- `judge_analytics` — judge behavior data (Phase 1 collection, Phase 2 feature)

### shared schema (1 table)
- `audit_logs` — platform-wide audit trail

## Migration Methods

### Method 1: Using Docker Compose (Recommended for Development)

**Step 1: Start services**
```bash
docker-compose up -d
```

**Step 2: Run migrations inside container**
```bash
docker-compose exec backend alembic upgrade head
```

**Step 3: Verify**
```bash
docker-compose exec backend python -c "
from backend.core.database import engine
import asyncio

async def check():
    async with engine.connect() as conn:
        result = await conn.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = \"law\"')
        tables = result.fetchall()
        for table in tables:
            print(f'✓ {table[0]}')

asyncio.run(check())
"
```

### Method 2: Direct Python (Local Development)

**Step 1: Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 2: Create .env file**
```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection string
# DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/nikhar
```

**Step 3: Run migrations**

**On Windows:**
```bash
run_migrations.bat
```

**On macOS/Linux:**
```bash
python run_migrations.py
```

### Method 3: Direct SQL (Advanced)

If you prefer to run SQL directly:

```bash
psql -U nikhar -d nikhar -f backend/migrations/versions/001_initial_schema.sql
```

Or from Python:
```python
import psycopg2
from backend.core.config import settings

conn = psycopg2.connect(settings.DATABASE_URL.replace('asyncpg://', '').replace('postgresql+asyncpg', 'postgresql'))
cursor = conn.cursor()

# Run migration SQL...
cursor.execute(...)

conn.commit()
cursor.close()
conn.close()
```

## Verification

### Check all tables exist

From PostgreSQL CLI:
```sql
-- List all law schema tables
\dt law.*

-- List all shared schema tables
\dt shared.*

-- Count rows (should all be 0 initially)
SELECT COUNT(*) FROM law.firms;
SELECT COUNT(*) FROM law.users;
SELECT COUNT(*) FROM law.matters;
-- ... etc
```

### From Python
```python
from backend.models import *
from backend.core.database import engine, AsyncSessionLocal
import asyncio
from sqlalchemy import text

async def verify_schema():
    async with AsyncSessionLocal() as session:
        tables = [
            'law.firms', 'law.users', 'law.matters', 'law.documents',
            'law.citations', 'law.drafts', 'law.search_history',
            'law.usage_logs', 'law.deadline_reminders', 'law.judge_analytics',
            'shared.audit_logs'
        ]
        
        for table in tables:
            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            )
            count = result.scalar()
            print(f"✓ {table} — {count} rows")

asyncio.run(verify_schema())
```

## Rollback

To rollback to previous migration version:

```bash
# Rollback one migration
alembic downgrade -1

# Rollback all
alembic downgrade base
```

From Docker:
```bash
docker-compose exec backend alembic downgrade -1
```

## Creating New Migrations

To create a new migration after modifying SQLAlchemy models:

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Add new_column to firms table"

# Review migration in backend/migrations/versions/
# Then run: alembic upgrade head
```

## Database Connection Troubleshooting

### Connection refused
```
Error: could not connect to server: Connection refused
```

**Solution:** Ensure PostgreSQL is running
```bash
docker-compose up -d postgres
docker-compose logs postgres  # Check for errors
```

### Database does not exist
```
Error: FATAL:  database "nikhar" does not exist
```

**Solution:** Create database
```bash
docker-compose exec postgres psql -U nikhar -c "CREATE DATABASE nikhar"
```

### Permission denied
```
Error: ERROR:  permission denied for schema law
```

**Solution:** Grant permissions
```sql
GRANT USAGE ON SCHEMA law TO nikhar;
GRANT CREATE ON SCHEMA law TO nikhar;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA law TO nikhar;
```

## Performance Notes

- All indexes are created during migration
- RLS is enabled on all tables (via `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`)
- Foreign keys are set up with proper constraints
- Soft delete indexes on `deleted_at` column for query efficiency

## Phase 1 Database Limits

All data is stored with firm isolation:
- Each row has `firm_id` for multi-tenancy
- RLS policies ensure cross-firm data leakage is impossible
- No global queries across firms (RLS enforces this)

## Next Steps After Migration

1. ✓ All tables created
2. Create firm account (insert into `law.firms`)
3. Create user account (insert into `law.users`)
4. Start uploading documents
5. Begin searches

See backend/api for endpoint documentation.
