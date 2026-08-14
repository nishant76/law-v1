"""Add law.matter_fee_installments

Backs the matter detail page's fees strip (Agreed / Paid / Due). Total Fees,
Paid, and Balance Due are computed from this table — no separate "agreed
total" column on matters, to avoid the two drifting out of sync.

Revision ID: 008_matter_fee_installments
Revises: 007_ecourts_name_match_check
Create Date: 2026-07-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '008_matter_fee_installments'
down_revision = '007_ecourts_name_match_check'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'matter_fee_installments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('law.firms.id'), nullable=False),
        sa.Column('matter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('law.matters.id'), nullable=False),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_paid', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('paid_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='law',
    )
    op.create_index('ix_matter_fee_installments_deleted_at', 'matter_fee_installments', ['deleted_at'], schema='law')
    op.create_index('ix_matter_fee_installments_firm_id', 'matter_fee_installments', ['firm_id'], schema='law')
    op.create_index('ix_matter_fee_installments_matter_id', 'matter_fee_installments', ['matter_id'], schema='law')
    op.execute('ALTER TABLE law.matter_fee_installments ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index('ix_matter_fee_installments_matter_id', table_name='matter_fee_installments', schema='law')
    op.drop_index('ix_matter_fee_installments_firm_id', table_name='matter_fee_installments', schema='law')
    op.drop_index('ix_matter_fee_installments_deleted_at', table_name='matter_fee_installments', schema='law')
    op.drop_table('matter_fee_installments', schema='law')
