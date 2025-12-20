"""fix_institutional_investors_timezone

Revision ID: 7d52b94302f9
Revises: bb640c20f0c7
Create Date: 2025-12-20 15:02:38.595475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d52b94302f9'
down_revision: Union[str, None] = 'bb640c20f0c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """修復 institutional_investors 表的時區問題"""
    # 將 created_at 改為 TIMESTAMP WITH TIME ZONE
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE
        USING created_at AT TIME ZONE 'UTC';
    """)

    # 將 updated_at 改為 TIMESTAMP WITH TIME ZONE
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE
        USING updated_at AT TIME ZONE 'UTC';
    """)


def downgrade() -> None:
    """回滾時區修改"""
    # 將 created_at 改回 TIMESTAMP WITHOUT TIME ZONE
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)

    # 將 updated_at 改回 TIMESTAMP WITHOUT TIME ZONE
    op.execute("""
        ALTER TABLE institutional_investors
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)
