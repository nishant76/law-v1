"""Initial schema for law vertical and shared audit logs

Revision ID: 001_initial
Revises: 
Create Date: 2026-04-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables and schemas"""
    
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create schemas
    op.execute('CREATE SCHEMA IF NOT EXISTS law')
    op.execute('CREATE SCHEMA IF NOT EXISTS shared')
    
    # ============================================================================
    # LAW SCHEMA TABLES
    # ============================================================================
    
    # firms table
    op.create_table(
        'firms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('plan', sa.String(50), nullable=False, server_default='trial'),
        sa.Column('trial_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('trial_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('collect_judge_data', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        schema='law'
    )
    op.create_index('ix_firms_deleted_at', 'firms', ['deleted_at'], schema='law')
    op.create_index('ix_firms_email', 'firms', ['email'], schema='law')
    op.create_index('ix_firms_is_active', 'firms', ['is_active'], schema='law')
    
    # users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('super_admin', 'firm_admin', 'lawyer', 'staff', 'trial', name='userrole'), nullable=False, server_default='lawyer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_token_issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['firm_id'], ['law.firms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        schema='law'
    )
    op.create_index('ix_users_deleted_at', 'users', ['deleted_at'], schema='law')
    op.create_index('ix_users_firm_id', 'users', ['firm_id'], schema='law')
    op.create_index('ix_users_email', 'users', ['email'], schema='law')
    op.create_index('ix_users_role', 'users', ['role'], schema='law')
    op.create_index('ix_users_is_active', 'users', ['is_active'], schema='law')
    
    # matters table
    op.create_table(
        'matters',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('matter_number', sa.String(100), nullable=True),
        sa.Column('case_name', sa.String(500), nullable=False),
        sa.Column('court', sa.String(255), nullable=True),
        sa.Column('judge_name', sa.String(255), nullable=True),
        sa.Column('matter_type', sa.String(100), nullable=True),
        sa.Column('petitioner', sa.String(500), nullable=True),
        sa.Column('respondent', sa.String(500), nullable=True),
        sa.Column('filing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_hearing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('limitation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('client_name', sa.String(255), nullable=True),
        sa.Column('client_phone', sa.String(20), nullable=True),
        sa.Column('whatsapp_reminders_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['law.firms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='law'
    )
    op.create_index('ix_matters_deleted_at', 'matters', ['deleted_at'], schema='law')
    op.create_index('ix_matters_firm_id', 'matters', ['firm_id'], schema='law')
    op.create_index('ix_matters_matter_number', 'matters', ['firm_id', 'matter_number'], schema='law')
    op.create_index('ix_matters_is_active', 'matters', ['is_active'], schema='law')

    # documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('matter_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('blob_path', sa.String(500), nullable=False),
        sa.Column('blob_url', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('pending', 'processing', 'indexed', 'failed', name='documentstatus'), nullable=False, server_default='pending'),
        sa.Column('error_reason', sa.Text(), nullable=True),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('search_index_name', sa.String(100), nullable=False, server_default='law-documents'),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('upload_source', sa.String(50), nullable=False, server_default='web'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['firm_id'], ['law.firms.id'], ),
        sa.ForeignKeyConstraint(['matter_id'], ['law.matters.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['law.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='law'
    )
    op.create_index('ix_documents_deleted_at', 'documents', ['deleted_at'], schema='law')
    op.create_index('ix_documents_firm_id', 'documents', ['firm_id'], schema='law')
    op.create_index('ix_documents_matter_id', 'documents', ['matter_id'], schema='law')
    op.create_index('ix_documents_status', 'documents', ['status'], schema='law')

    # citations table
    op.create_table(
        'citations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('citation_key', sa.String(100), nullable=False),
        sa.Column('case_name', sa.String(500), nullable=False),
        sa.Column('court', sa.String(255), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('petitioner', sa.String(500), nullable=True),
        sa.Column('respondent', sa.String(500), nullable=True),
        sa.Column('judge_name', sa.String(255), nullable=True),
        sa.Column('judgment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('judgment_text', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('matter_type', sa.String(100), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('official_source', sa.String(100), nullable=False),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('embedding_vector', sa.String(10000), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('citation_key'),
        schema='law'
    )
    op.create_index('ix_citations_deleted_at', 'citations', ['deleted_at'], schema='law')
    op.create_index('ix_citations_citation_key', 'citations', ['citation_key'], schema='law')
    op.create_index('ix_citations_case_name', 'citations', ['case_name'], schema='law')
    op.create_index('ix_citations_court', 'citations', ['court'], schema='law')
    op.create_index('ix_citations_year', 'citations', ['year'], schema='law')
    op.create_index('ix_citations_matter_type', 'citations', ['matter_type'], schema='law')

    # drafts table
    op.create_table(
        'drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('matter_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('draft_type', sa.Enum('case_synopsis', 'smart_reply', 'filing_draft', 'other', name='drafttype'), nullable=False),
        sa.Column('status', sa.Enum('generating', 'generated', 'accepted', 'rejected', name='draftstatus'), nullable=False, server_default='generating'),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('citation_safety_score', sa.Integer(), nullable=True),
        sa.Column('completeness_score', sa.Integer(), nullable=True),
        sa.Column('legal_accuracy_score', sa.Integer(), nullable=True),
        sa.Column('language_score', sa.Integer(), nullable=True),
        sa.Column('generated_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('filing_objective', sa.String(100), nullable=True),
        sa.Column('accepted_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exported_format', sa.String(50), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['law.firms.id'], ),
        sa.ForeignKeyConstraint(['matter_id'], ['law.matters.id'], ),
        sa.ForeignKeyConstraint(['generated_by_user_id'], ['law.users.id'], ),
        sa.ForeignKeyConstraint(['accepted_by_user_id'], ['law.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='law'
    )
    op.create_index('ix_drafts_deleted_at', 'drafts', ['deleted_at'], schema='law')
    op.create_index('ix_drafts_firm_id', 'drafts', ['firm_id'], schema='law')
    op.create_index('ix_drafts_matter_id', 'drafts', ['matter_id'], schema='law')
    op.create_index('ix_drafts_status', 'drafts', ['status'], schema='law')
    op.create_index('ix_drafts_draft_type', 'drafts', ['draft_type'], schema='law')

    # search_history table
    op.create_table(
        'search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('search_scope', sa.String(100), nullable=False, server_default='both'),
        sa.Column('results_from_own_documents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results_from_public_judgments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('search_filters', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['law.firms.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['law.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='law'
    )
    op.create_index('ix_search_history_deleted_at', 'search_history', ['deleted_at'], schema='law')
    op.create_index('ix_search_history_firm_id', 'search_history', ['firm_id'], schema='law')
    op.create_index('ix_search_history_user_id', 'search_history', ['user_id'], schema='law')
    op.create_index('ix_search_history_created_at', 'search_history', ['created_at'], schema='law')

    # usage_logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['law.firms.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['law.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='law'
    )
    op.create_index('ix_usage_logs_deleted_at', 'usage_logs', ['deleted_at'], schema='law')
    op.create_index('ix_usage_logs_firm_id', 'usage_logs', ['firm_id'], schema='law')
    op.create_index('ix_usage_logs_created_at', 'usage_logs', ['created_at'], schema='law')
    op.create_index('ix_usage_logs_action', 'usage_logs', ['action'], schema='law')

    # deadline_reminders table
    op.create_table(
        'deadline_reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('matter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reminder_type', sa.Enum('hearing', 'filing_deadline', 'limitation_period', 'urgent', name='remindertype'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('key_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reminder_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'sent', 'missed', name='reminderstatus'), nullable=False, server_default='pending'),
        sa.Column('email_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('whatsapp_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('whatsapp_message_template', sa.String(1000), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('missed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['law.firms.id'], ),
        sa.ForeignKeyConstraint(['matter_id'], ['law.matters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='law'
    )
    op.create_index('ix_deadline_reminders_deleted_at', 'deadline_reminders', ['deleted_at'], schema='law')
    op.create_index('ix_deadline_reminders_firm_id', 'deadline_reminders', ['firm_id'], schema='law')
    op.create_index('ix_deadline_reminders_matter_id', 'deadline_reminders', ['matter_id'], schema='law')
    op.create_index('ix_deadline_reminders_reminder_date', 'deadline_reminders', ['reminder_date'], schema='law')
    op.create_index('ix_deadline_reminders_reminder_type', 'deadline_reminders', ['reminder_type'], schema='law')

    # judge_analytics table
    op.create_table(
        'judge_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('judge_name', sa.String(255), nullable=False),
        sa.Column('court', sa.String(255), nullable=False),
        sa.Column('matter_type', sa.String(100), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('citation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('transferred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['citation_id'], ['law.citations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='law'
    )
    op.create_index('ix_judge_analytics_deleted_at', 'judge_analytics', ['deleted_at'], schema='law')
    op.create_index('ix_judge_analytics_judge_name', 'judge_analytics', ['judge_name'], schema='law')
    op.create_index('ix_judge_analytics_court', 'judge_analytics', ['court'], schema='law')
    op.create_index('ix_judge_analytics_year', 'judge_analytics', ['year'], schema='law')
    op.create_index('ix_judge_analytics_matter_type', 'judge_analytics', ['matter_type'], schema='law')

    # ============================================================================
    # SHARED SCHEMA TABLES
    # ============================================================================
    
    # audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('http_method', sa.String(10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='shared'
    )
    op.create_index('ix_audit_logs_deleted_at', 'audit_logs', ['deleted_at'], schema='shared')
    op.create_index('ix_audit_logs_firm_id', 'audit_logs', ['firm_id'], schema='shared')
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], schema='shared')
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], schema='shared')
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], schema='shared')
    
    # ============================================================================
    # ROW LEVEL SECURITY (RLS) — PostgreSQL
    # ============================================================================
    
    # Enable RLS on all law schema tables
    op.execute('ALTER TABLE law.firms ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.users ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.matters ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.documents ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.citations ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.drafts ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.search_history ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.usage_logs ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.deadline_reminders ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE law.judge_analytics ENABLE ROW LEVEL SECURITY')
    
    # Enable RLS on shared schema tables
    op.execute('ALTER TABLE shared.audit_logs ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Drop all tables and schemas"""
    
    # Drop law schema tables
    op.drop_table('judge_analytics', schema='law')
    op.drop_table('deadline_reminders', schema='law')
    op.drop_table('usage_logs', schema='law')
    op.drop_table('search_history', schema='law')
    op.drop_table('drafts', schema='law')
    op.drop_table('citations', schema='law')
    op.drop_table('documents', schema='law')
    op.drop_table('matters', schema='law')
    op.drop_table('users', schema='law')
    op.drop_table('firms', schema='law')
    
    # Drop shared schema tables
    op.drop_table('audit_logs', schema='shared')
    
    # Drop schemas
    op.execute('DROP SCHEMA IF EXISTS law CASCADE')
    op.execute('DROP SCHEMA IF EXISTS shared CASCADE')
