"""fix_option_tables_timezone

Revision ID: 963973af160f
Revises: 7d52b94302f9
Create Date: 2025-12-20 15:06:38.111901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '963973af160f'
down_revision: Union[str, None] = '7d52b94302f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """修復 Option 表的時區問題"""
    # option_contracts 表
    op.execute("""
        ALTER TABLE option_contracts
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC';
    """)
    op.execute("""
        ALTER TABLE option_contracts
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        USING updated_at AT TIME ZONE 'UTC';
    """)

    # option_daily_factors 表
    op.execute("""
        ALTER TABLE option_daily_factors
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC';
    """)

    # option_sync_config 表
    op.execute("""
        ALTER TABLE option_sync_config
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        USING updated_at AT TIME ZONE 'UTC';
    """)


def downgrade() -> None:
    """回滾時區修改"""
    # option_sync_config 表
    op.execute("""
        ALTER TABLE option_sync_config
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)

    # option_daily_factors 表
    op.execute("""
        ALTER TABLE option_daily_factors
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)

    # option_contracts 表
    op.execute("""
        ALTER TABLE option_contracts
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
    op.execute("""
        ALTER TABLE option_contracts
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
