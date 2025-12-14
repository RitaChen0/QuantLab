"""add_telegram_notifications_tables

Revision ID: 14b5df59adf4
Revises: 20251213_inst_inv
Create Date: 2025-12-13 23:25:17.148960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14b5df59adf4'
down_revision: Union[str, None] = '20251213_inst_inv'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create telegram_notifications table
    op.create_table(
        'telegram_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('telegram_message_id', sa.BigInteger(), nullable=True),
        sa.Column('has_image', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('related_object_type', sa.String(length=50), nullable=True),
        sa.Column('related_object_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for telegram_notifications
    op.create_index('ix_telegram_notifications_user_id', 'telegram_notifications', ['user_id'])
    op.create_index('ix_telegram_notifications_type', 'telegram_notifications', ['notification_type'])
    op.create_index('ix_telegram_notifications_status', 'telegram_notifications', ['status'])
    op.create_index('ix_telegram_notifications_created_at', 'telegram_notifications', ['created_at'])

    # Create telegram_notification_preferences table
    op.create_table(
        'telegram_notification_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('backtest_completed_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('rdagent_completed_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('market_alert_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quiet_hours_start', sa.Time(), nullable=True),
        sa.Column('quiet_hours_end', sa.Time(), nullable=True),
        sa.Column('include_charts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_telegram_preferences_user_id')
    )

    # Create index for telegram_notification_preferences
    op.create_index('ix_telegram_preferences_user_id', 'telegram_notification_preferences', ['user_id'], unique=True)


def downgrade() -> None:
    # Drop telegram_notification_preferences table
    op.drop_index('ix_telegram_preferences_user_id', table_name='telegram_notification_preferences')
    op.drop_table('telegram_notification_preferences')

    # Drop telegram_notifications table
    op.drop_index('ix_telegram_notifications_created_at', table_name='telegram_notifications')
    op.drop_index('ix_telegram_notifications_status', table_name='telegram_notifications')
    op.drop_index('ix_telegram_notifications_type', table_name='telegram_notifications')
    op.drop_index('ix_telegram_notifications_user_id', table_name='telegram_notifications')
    op.drop_table('telegram_notifications')
