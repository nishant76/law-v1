"""Add ecourts_name_match_found to law.users

Tri-state flag for the "check once" identity-match rule:
  - NULL  -> the lawyer's advocate name has never been checked against eCourts yet
  - TRUE  -> the first check found pending cases under their name
  - FALSE -> the first check found nothing; the app stops auto-checking and
             always shows the manual case-search box instead

Set once, on the first successful call to preview-my-cases, and never
overwritten afterwards (see backend/api/ecourts.py).

Revision ID: 007_ecourts_name_match_check
Revises: 006_ecourts_bar_council
Create Date: 2026-07-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '007_ecourts_name_match_check'
down_revision = '006_ecourts_bar_council'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('ecourts_name_match_found', sa.Boolean(), nullable=True),
        schema='law',
    )


def downgrade() -> None:
    op.drop_column('users', 'ecourts_name_match_found', schema='law')
