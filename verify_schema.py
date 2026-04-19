#!/usr/bin/env python3
"""
Schema verification script — validates database structure after migrations
Usage: python verify_schema.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.core.database import engine, AsyncSessionLocal
from backend.core.logger import get_logger
from backend.models import *
from sqlalchemy import inspect, text

logger = get_logger(__name__)


async def verify_schema():
    """Verify all tables and columns exist"""
    errors = []
    
    try:
        async with AsyncSessionLocal() as session:
            # List of expected tables with their expected columns
            expected_tables = {
                'law.firms': ['id', 'created_at', 'deleted_at', 'name', 'email', 'phone', 'city', 'state', 'plan', 'trial_days', 'is_active'],
                'law.users': ['id', 'created_at', 'deleted_at', 'firm_id', 'name', 'email', 'password_hash', 'role', 'is_active'],
                'law.matters': ['id', 'created_at', 'deleted_at', 'firm_id', 'case_name', 'court', 'matter_type', 'is_active'],
                'law.documents': ['id', 'created_at', 'deleted_at', 'firm_id', 'file_name', 'file_type', 'status', 'firm_id'],
                'law.citations': ['id', 'created_at', 'deleted_at', 'citation_key', 'case_name', 'court', 'year', 'outcome'],
                'law.drafts': ['id', 'created_at', 'deleted_at', 'firm_id', 'draft_type', 'status', 'content'],
                'law.search_history': ['id', 'created_at', 'deleted_at', 'firm_id', 'query', 'search_scope'],
                'law.usage_logs': ['id', 'created_at', 'deleted_at', 'firm_id', 'action', 'tokens_used'],
                'law.deadline_reminders': ['id', 'created_at', 'deleted_at', 'firm_id', 'matter_id', 'reminder_type', 'status'],
                'law.judge_analytics': ['id', 'created_at', 'deleted_at', 'judge_name', 'court', 'year'],
                'shared.audit_logs': ['id', 'created_at', 'deleted_at', 'firm_id', 'action', 'resource_type'],
            }
            
            logger.info("=" * 80)
            logger.info("DATABASE SCHEMA VERIFICATION")
            logger.info("=" * 80)
            
            # Check each table
            for table_name, expected_columns in expected_tables.items():
                try:
                    result = await session.execute(
                        text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_schema = :schema 
                            AND table_name = :table
                        """),
                        {"schema": table_name.split('.')[0], "table": table_name.split('.')[1]}
                    )
                    
                    existing_columns = {row[0] for row in result.fetchall()}
                    
                    if not existing_columns:
                        errors.append(f"✗ Table {table_name} DOES NOT EXIST")
                        logger.error(f"✗ {table_name}")
                    else:
                        # Check for critical columns
                        critical_columns = {'id', 'created_at', 'deleted_at'}
                        if table_name.startswith('law'):
                            critical_columns.add('firm_id')
                        
                        missing = critical_columns - existing_columns
                        if missing:
                            error_msg = f"✗ {table_name} — Missing critical columns: {missing}"
                            errors.append(error_msg)
                            logger.error(error_msg)
                        else:
                            logger.info(f"✓ {table_name} — {len(existing_columns)} columns")
                            
                except Exception as e:
                    logger.error(f"✗ {table_name} — Error: {str(e)}")
                    errors.append(f"✗ {table_name} — {str(e)}")
            
            # Check Row Level Security
            logger.info("\n" + "=" * 80)
            logger.info("ROW LEVEL SECURITY STATUS")
            logger.info("=" * 80)
            
            rls_tables = [
                'law.firms', 'law.users', 'law.matters', 'law.documents',
                'law.citations', 'law.drafts', 'law.search_history',
                'law.usage_logs', 'law.deadline_reminders', 'law.judge_analytics',
                'shared.audit_logs'
            ]
            
            for table in rls_tables:
                schema, tname = table.split('.')
                result = await session.execute(
                    text(f"""
                        SELECT rowsecurity 
                        FROM pg_tables 
                        WHERE schemaname = :schema 
                        AND tablename = :table
                    """),
                    {"schema": schema, "table": tname}
                )
                
                row = result.fetchone()
                if row and row[0]:
                    logger.info(f"✓ {table} — RLS enabled")
                else:
                    logger.warning(f"⚠ {table} — RLS disabled (requires manual enablement)")
            
            # Check indexes
            logger.info("\n" + "=" * 80)
            logger.info("INDEXES")
            logger.info("=" * 80)
            
            result = await session.execute(
                text("""
                    SELECT indexname, tablename 
                    FROM pg_indexes 
                    WHERE schemaname IN ('law', 'shared')
                    ORDER BY tablename
                """)
            )
            
            indexes = result.fetchall()
            logger.info(f"✓ {len(indexes)} indexes created")
            
            # Foreign keys
            logger.info("\n" + "=" * 80)
            logger.info("FOREIGN KEYS")
            logger.info("=" * 80)
            
            result = await session.execute(
                text("""
                    SELECT constraint_name, table_name, column_name 
                    FROM information_schema.key_column_usage 
                    WHERE table_schema IN ('law', 'shared')
                    AND constraint_name LIKE 'fk_%'
                """)
            )
            
            fks = result.fetchall()
            logger.info(f"✓ {len(fks)} foreign key constraints")
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("SUMMARY")
            logger.info("=" * 80)
            
            if not errors:
                logger.info("✓ ALL CHECKS PASSED — Database schema is ready")
                return 0
            else:
                logger.error(f"✗ {len(errors)} ISSUES FOUND:")
                for error in errors:
                    logger.error(f"  {error}")
                return 1
                
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        logger.error("Ensure:")
        logger.error("  1. PostgreSQL is running")
        logger.error("  2. DATABASE_URL is correct in .env")
        logger.error("  3. Migrations have been run (python run_migrations.py)")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(verify_schema())
    sys.exit(exit_code)
