"""Add CASCADE to stock_minute_prices foreign key

Revision ID: 07b5643328f2
Revises: 4b53b67e4e01
Create Date: 2025-12-26 14:14:52.834276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07b5643328f2'
down_revision: Union[str, None] = '4b53b67e4e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing foreign key constraint without CASCADE
    op.drop_constraint(
        'stock_minute_prices_stock_id_fkey',
        'stock_minute_prices',
        type_='foreignkey'
    )

    # Re-create foreign key constraint with CASCADE
    op.create_foreign_key(
        'stock_minute_prices_stock_id_fkey',
        'stock_minute_prices',
        'stocks',
        ['stock_id'],
        ['stock_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Revert to foreign key without CASCADE (original state)
    op.drop_constraint(
        'stock_minute_prices_stock_id_fkey',
        'stock_minute_prices',
        type_='foreignkey'
    )

    # Re-create without CASCADE
    op.create_foreign_key(
        'stock_minute_prices_stock_id_fkey',
        'stock_minute_prices',
        'stocks',
        ['stock_id'],
        ['stock_id']
    )
