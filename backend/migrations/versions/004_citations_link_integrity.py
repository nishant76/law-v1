"""Add link-integrity columns to law.citations

Enforces the LAUNCH QUALITY MANDATE for citation links:
- blob_path:        path to our self-hosted copy of the public-domain judgment PDF
                    (primary "View Judgment" link — can never break)
- link_status:      'pending' | 'verified' | 'self_hosted' | 'dead'
- link_checked_at:  when source_url / blob copy was last validated

source_url (existing) is retained as the official government link, shown as a
secondary "View on official source" link.

Revision ID: 004_citations_link_integrity
Revises: 003_citations_add_enrichment
Create Date: 2026-06-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '004_citations_link_integrity'
down_revision = '003_citations_add_enrichment'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('citations', sa.Column('blob_path', sa.String(500), nullable=True), schema='law')
    op.add_column(
        'citations',
        sa.Column('link_status', sa.String(20), nullable=False, server_default='pending'),
        schema='law',
    )
    op.add_column(
        'citations',
        sa.Column('link_checked_at', sa.DateTime(timezone=True), nullable=True),
        schema='law',
    )
    # Index used by search to surface only citations with a working link.
    op.create_index(
        'ix_citations_link_status',
        'citations',
        ['link_status'],
        schema='law',
    )


def downgrade() -> None:
    op.drop_index('ix_citations_link_status', table_name='citations', schema='law')
    op.drop_column('citations', 'link_checked_at', schema='law')
    op.drop_column('citations', 'link_status', schema='law')
    op.drop_column('citations', 'blob_path', schema='law')
