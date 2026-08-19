"""Add a 'completed' reminder status

Without it, a reminder for a hearing the lawyer actually attended stays 'sent'
forever. Once its key date passes, the deadlines API classifies it
urgency="missed", so every attended hearing accumulates in the Missed panel —
which is how a reminder feature trains people to ignore it.

Soft-deleting the row instead would lose the record that a reminder WAS sent,
so this adds a terminal status rather than removing history.

Revision ID: 010_reminder_completed_status
Revises: 009_notifications_and_diary
Create Date: 2026-08-19 00:00:00.000000
"""
from alembic import op

revision = '010_reminder_completed_status'
down_revision = '009_notifications_and_diary'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL 12+ allows ADD VALUE inside a transaction as long as the new
    # label is not USED in the same transaction — this migration only adds it.
    op.execute("ALTER TYPE reminderstatus ADD VALUE IF NOT EXISTS 'completed'")


def downgrade() -> None:
    # PostgreSQL cannot drop a value from an enum. Any row already carrying
    # 'completed' is moved back to 'sent' (its previous meaning: delivered, and
    # the date has passed) so the type stays usable if this is ever reverted.
    op.execute("UPDATE law.deadline_reminders SET status = 'sent' WHERE status = 'completed'")
