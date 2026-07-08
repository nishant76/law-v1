"""Add bar council number + eCourts state code to law.users

law.users gains:
  - bar_council_number   enrollment number from state bar council (e.g. P/1234/2020)
  - ecourts_state_code   eCourts numeric state code (e.g. "3" for Punjab)

These replace the need for a licensed vendor API — the mobile app API uses
bar_council_number (bar code mode) + state_code to pull all of an advocate's
pending cases directly.

Revision ID: 006_ecourts_bar_council
Revises: 005_ecourts_integration
Create Date: 2026-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '006_ecourts_bar_council'
down_revision = '005_ecourts_integration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('bar_council_number', sa.String(50), nullable=True), schema='law')
    op.add_column('users', sa.Column('ecourts_state_code', sa.String(10), nullable=True), schema='law')


def downgrade() -> None:
    op.drop_column('users', 'ecourts_state_code', schema='law')
    op.drop_column('users', 'bar_council_number', schema='law')
