"""Add unique constraint to institutional_investors

Revision ID: 8bebe110b823
Revises: 07b5643328f2
Create Date: 2025-12-26 14:15:53.562399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bebe110b823'
down_revision: Union[str, None] = '07b5643328f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint on (stock_id, date, investor_type)
    # This prevents duplicate records for the same stock, date, and investor type
    op.create_unique_constraint(
        'uq_institutional_investors_stock_date_type',
        'institutional_investors',
        ['stock_id', 'date', 'investor_type']
    )


def downgrade() -> None:
    # Remove unique constraint
    op.drop_constraint(
        'uq_institutional_investors_stock_date_type',
        'institutional_investors',
        type_='unique'
    )
