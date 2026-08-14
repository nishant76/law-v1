"""Add law.notifications, law.hearing_entries, and lawyer diary opt-in fields

Closes the gap where deadline reminders had no delivery target at all:
  * law.notifications  — in-app notification feed (the channel that always works)
  * law.hearing_entries — the diary proper: one row per court date per matter,
    recording board number, stage, what happened, and the adjourned-to date
  * law.users.whatsapp_number / daily_cause_list_enabled — opt-in for the
    lawyer's own next-day cause list on WhatsApp

Revision ID: 009_notifications_and_diary
Revises: 008_matter_fee_installments
Create Date: 2026-08-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009_notifications_and_diary'
down_revision = '008_matter_fee_installments'
branch_labels = None
depends_on = None

NOTIFICATION_TYPES = (
    'hearing', 'deadline', 'deadline_missed', 'ecourts_sync', 'document', 'system',
)
HEARING_STATUSES = (
    'scheduled', 'held', 'adjourned', 'not_taken_up', 'disposed',
)


def upgrade() -> None:
    # Enum types live in the default (public) schema, matching 001_initial —
    # the ORM models declare Enum(...) without a schema, so they must agree.
    notification_type = sa.Enum(*NOTIFICATION_TYPES, name='notificationtype')
    hearing_status = sa.Enum(*HEARING_STATUSES, name='hearingstatus')
    notification_type.create(op.get_bind(), checkfirst=True)
    hearing_status.create(op.get_bind(), checkfirst=True)
    # Types are created explicitly above; stop create_table from re-issuing them.
    notification_type = postgresql.ENUM(
        *NOTIFICATION_TYPES, name='notificationtype', create_type=False
    )
    hearing_status = postgresql.ENUM(
        *HEARING_STATUSES, name='hearingstatus', create_type=False
    )

    # ------------------------------------------------------------ notifications
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('law.firms.id'), nullable=False),
        # NULL user_id = firm-wide notification.
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('law.users.id'), nullable=True),
        sa.Column('matter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('law.matters.id'), nullable=True),
        sa.Column('notification_type', notification_type, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('link_path', sa.String(500), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        schema='law',
    )
    op.create_index('ix_notifications_deleted_at', 'notifications', ['deleted_at'], schema='law')
    op.create_index('ix_notifications_firm_id', 'notifications', ['firm_id'], schema='law')
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], schema='law')
    op.create_index('ix_notifications_read_at', 'notifications', ['read_at'], schema='law')
    op.create_index('ix_notifications_notification_type', 'notifications',
                    ['notification_type'], schema='law')
    op.execute('ALTER TABLE law.notifications ENABLE ROW LEVEL SECURITY')

    # ---------------------------------------------------------- hearing_entries
    op.create_table(
        'hearing_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('firm_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('law.firms.id'), nullable=False),
        sa.Column('matter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('law.matters.id'), nullable=False),
        sa.Column('hearing_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', hearing_status, nullable=False,
                  server_default=sa.text("'scheduled'")),
        sa.Column('court', sa.String(255), nullable=True),
        sa.Column('judge_name', sa.String(255), nullable=True),
        sa.Column('board_number', sa.String(20), nullable=True),
        sa.Column('purpose', sa.String(255), nullable=True),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('adjournment_reason', sa.String(500), nullable=True),
        sa.Column('next_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_required', sa.Text(), nullable=True),
        sa.Column('appeared_by', sa.String(255), nullable=True),
        sa.Column('from_ecourts', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('law.users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        schema='law',
    )
    op.create_index('ix_hearing_entries_deleted_at', 'hearing_entries', ['deleted_at'], schema='law')
    op.create_index('ix_hearing_entries_firm_id', 'hearing_entries', ['firm_id'], schema='law')
    op.create_index('ix_hearing_entries_matter_id', 'hearing_entries', ['matter_id'], schema='law')
    op.create_index('ix_hearing_entries_hearing_date', 'hearing_entries',
                    ['hearing_date'], schema='law')
    op.create_index('ix_hearing_entries_status', 'hearing_entries', ['status'], schema='law')
    # The eCourts sync upserts one scheduled row per (matter, date); this keeps
    # a repeated sync from stacking duplicates of the same listing.
    op.create_index(
        'uq_hearing_entries_matter_date', 'hearing_entries',
        ['matter_id', 'hearing_date'], unique=True, schema='law',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.execute('ALTER TABLE law.hearing_entries ENABLE ROW LEVEL SECURITY')

    # ----------------------------------------------------- users diary opt-in
    op.add_column('users', sa.Column('whatsapp_number', sa.String(20), nullable=True),
                  schema='law')
    op.add_column('users', sa.Column('daily_cause_list_enabled', sa.Boolean(),
                                     nullable=False, server_default=sa.text('false')),
                  schema='law')


def downgrade() -> None:
    op.drop_column('users', 'daily_cause_list_enabled', schema='law')
    op.drop_column('users', 'whatsapp_number', schema='law')

    op.drop_index('uq_hearing_entries_matter_date', table_name='hearing_entries', schema='law')
    op.drop_index('ix_hearing_entries_status', table_name='hearing_entries', schema='law')
    op.drop_index('ix_hearing_entries_hearing_date', table_name='hearing_entries', schema='law')
    op.drop_index('ix_hearing_entries_matter_id', table_name='hearing_entries', schema='law')
    op.drop_index('ix_hearing_entries_firm_id', table_name='hearing_entries', schema='law')
    op.drop_index('ix_hearing_entries_deleted_at', table_name='hearing_entries', schema='law')
    op.drop_table('hearing_entries', schema='law')

    op.drop_index('ix_notifications_notification_type', table_name='notifications', schema='law')
    op.drop_index('ix_notifications_read_at', table_name='notifications', schema='law')
    op.drop_index('ix_notifications_user_id', table_name='notifications', schema='law')
    op.drop_index('ix_notifications_firm_id', table_name='notifications', schema='law')
    op.drop_index('ix_notifications_deleted_at', table_name='notifications', schema='law')
    op.drop_table('notifications', schema='law')

    bind = op.get_bind()
    postgresql.ENUM(name='hearingstatus').drop(bind, checkfirst=True)
    postgresql.ENUM(name='notificationtype').drop(bind, checkfirst=True)
