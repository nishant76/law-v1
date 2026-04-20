"""Add enrichment JSONB column to law.citations

Stores AI-generated per-citation metadata (facts, issue, reasoning, ratio, relevance).
Generated once via Celery background task and reused forever — cached at citation level.

Revision ID: 003_citations_add_enrichment
Revises: 002_citations_add_fields
Create Date: 2026-04-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '003_citations_add_enrichment'
down_revision = '002_citations_add_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'citations',
        sa.Column('enrichment', JSONB, nullable=True),
        schema='law',
    )
    # Partial index: only index rows that have been enriched (avoids large null index)
    op.create_index(
        'ix_citations_enrichment_not_null',
        'citations',
        ['id'],
        schema='law',
        postgresql_where=sa.text('enrichment IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'ix_citations_enrichment_not_null',
        table_name='citations',
        schema='law',
    )
    op.drop_column('citations', 'enrichment', schema='law')
