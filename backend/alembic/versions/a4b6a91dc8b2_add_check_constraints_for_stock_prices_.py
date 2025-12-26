"""Add CHECK constraints for stock_prices data quality

Revision ID: a4b6a91dc8b2
Revises: 8bebe110b823
Create Date: 2025-12-26 14:35:27.892080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b6a91dc8b2'
down_revision: Union[str, None] = '8bebe110b823'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CHECK constraint: high >= low
    op.create_check_constraint(
        'chk_stock_prices_high_low',
        'stock_prices',
        'high >= low'
    )

    # Add CHECK constraint: close between low and high (or all zeros)
    # Allow close to be outside range only if it's part of an all-zero record
    op.create_check_constraint(
        'chk_stock_prices_close_range',
        'stock_prices',
        '(close BETWEEN low AND high) OR (open = 0 AND high = 0 AND low = 0 AND close = 0)'
    )

    # Add CHECK constraint: prevent zero prices (except for placeholder records)
    # Either all OHLC > 0, OR all OHLC = 0 (placeholder)
    op.create_check_constraint(
        'chk_stock_prices_positive',
        'stock_prices',
        '(open > 0 AND high > 0 AND low > 0 AND close > 0) OR (open = 0 AND high = 0 AND low = 0 AND close = 0)'
    )


def downgrade() -> None:
    # Remove CHECK constraints in reverse order
    op.drop_constraint('chk_stock_prices_positive', 'stock_prices', type_='check')
    op.drop_constraint('chk_stock_prices_close_range', 'stock_prices', type_='check')
    op.drop_constraint('chk_stock_prices_high_low', 'stock_prices', type_='check')
