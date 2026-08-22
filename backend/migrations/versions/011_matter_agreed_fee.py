"""Add agreed_fee to matters

Lawyers set a total fee per matter up front. Installments track the payment
schedule. The agreed_fee is the number the lawyer quoted the client — it
doesn't have to equal the sum of installments (partial billing is common).

Revision ID: 011_matter_agreed_fee
Revises: 010_reminder_completed_status
Create Date: 2026-08-20 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = '011_matter_agreed_fee'
down_revision = '010_reminder_completed_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('matters', sa.Column('agreed_fee', sa.Numeric(12, 2), nullable=True), schema='law')


def downgrade() -> None:
    op.drop_column('matters', 'agreed_fee', schema='law')
