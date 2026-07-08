"""Add eCourts integration columns

law.matters:
  - cnr_number        16-char Case Number Record used to fetch eCourts data
  - case_status       PENDING / DISPOSED / … as reported by eCourts
  - ecourts_synced_at when this matter was last synced from eCourts
  - ecourts_tracked   matter auto-created/maintained from an eCourts sync

law.users:
  - ecourts_advocate_name  the lawyer's advocate name as registered on eCourts,
                           used to look up their cases / hearing dates

Revision ID: 005_ecourts_integration
Revises: 004_citations_link_integrity
Create Date: 2026-06-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '005_ecourts_integration'
down_revision = '004_citations_link_integrity'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('matters', sa.Column('cnr_number', sa.String(20), nullable=True), schema='law')
    op.add_column('matters', sa.Column('case_status', sa.String(50), nullable=True), schema='law')
    op.add_column('matters', sa.Column('ecourts_synced_at', sa.DateTime(timezone=True), nullable=True), schema='law')
    op.add_column(
        'matters',
        sa.Column('ecourts_tracked', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='law',
    )
    op.create_index('ix_matters_cnr_number', 'matters', ['cnr_number'], schema='law')

    op.add_column('users', sa.Column('ecourts_advocate_name', sa.String(255), nullable=True), schema='law')


def downgrade() -> None:
    op.drop_column('users', 'ecourts_advocate_name', schema='law')
    op.drop_index('ix_matters_cnr_number', table_name='matters', schema='law')
    op.drop_column('matters', 'ecourts_tracked', schema='law')
    op.drop_column('matters', 'ecourts_synced_at', schema='law')
    op.drop_column('matters', 'case_status', schema='law')
    op.drop_column('matters', 'cnr_number', schema='law')
