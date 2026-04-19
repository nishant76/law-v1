# alembic — Database migrations

This directory contains Alembic migrations for schema version control.

## Usage

**Create a new migration:**
```bash
docker-compose exec backend alembic revision --autogenerate -m "Add users table"
```

**Apply migrations:**
```bash
docker-compose exec backend alembic upgrade head
```

**Rollback one migration:**
```bash
docker-compose exec backend alembic downgrade -1
```

See Alembic docs: https://alembic.sqlalchemy.org/

## Migration Rules (Phase 1)

1. All new columns must have DEFAULT value where sensible
2. Never drop columns without migration (soft delete instead)
3. Every table must have:
   - `id` (UUID, PRIMARY KEY)
   - `created_at` (TIMESTAMPTZ, DEFAULT NOW())
   - `deleted_at` (TIMESTAMPTZ, nullable)
4. Law schema tables must have:
   - `firm_id` (UUID, NOT NULL)
5. Enable Row Level Security (RLS) on every table
6. Use raw SQL for complex operations
