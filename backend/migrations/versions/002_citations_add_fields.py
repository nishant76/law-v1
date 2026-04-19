"""Add primary_citation, subject_tags, source_doc_id to law.citations

Revision ID: 002_citations_add_fields
Revises: 001_initial
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_citations_add_fields'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'citations',
        sa.Column('primary_citation', sa.String(200), nullable=True),
        schema='law',
    )
    op.add_column(
        'citations',
        sa.Column('subject_tags', sa.Text(), nullable=True),
        schema='law',
    )
    op.add_column(
        'citations',
        sa.Column('source_doc_id', sa.String(100), nullable=True),
        schema='law',
    )
    op.create_index(
        'ix_citations_source_doc_id',
        'citations',
        ['source_doc_id'],
        schema='law',
    )


def downgrade() -> None:
    op.drop_index('ix_citations_source_doc_id', table_name='citations', schema='law')
    op.drop_column('citations', 'source_doc_id', schema='law')
    op.drop_column('citations', 'subject_tags', schema='law')
    op.drop_column('citations', 'primary_citation', schema='law')
