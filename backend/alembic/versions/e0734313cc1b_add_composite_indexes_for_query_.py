"""add_composite_indexes_for_query_optimization

Revision ID: e0734313cc1b
Revises: a4b6a91dc8b2
Create Date: 2025-12-26 14:44:20.305976

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0734313cc1b'
down_revision: Union[str, None] = 'a4b6a91dc8b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. stock_prices: DESC ordering for time-series queries (recent prices first)
    op.create_index(
        'idx_stock_prices_stock_date_desc',
        'stock_prices',
        ['stock_id', sa.text('date DESC')],
        unique=False
    )

    # 2. institutional_investors: DESC ordering for recent data queries
    op.create_index(
        'idx_institutional_stock_date_desc',
        'institutional_investors',
        ['stock_id', sa.text('date DESC')],
        unique=False
    )

    # 3. institutional_investors: Market-wide analysis by date
    op.create_index(
        'idx_institutional_date_type',
        'institutional_investors',
        [sa.text('date DESC'), 'investor_type'],
        unique=False
    )

    # 4. stock_minute_prices: DESC ordering for recent minute data
    op.create_index(
        'idx_minute_stock_timeframe_datetime_desc',
        'stock_minute_prices',
        ['stock_id', 'timeframe', sa.text('datetime DESC')],
        unique=False
    )

    # 5. fundamental_data: DESC ordering for latest fundamental data
    op.create_index(
        'idx_fundamental_stock_indicator_date_desc',
        'fundamental_data',
        ['stock_id', 'indicator', sa.text('date DESC')],
        unique=False
    )

    # 6. trades: Composite index for trade analysis (already have backtest_date, add DESC)
    op.create_index(
        'idx_trades_backtest_stock_date_desc',
        'trades',
        ['backtest_id', 'stock_id', sa.text('date DESC')],
        unique=False
    )

    # 7. backtests: Partial index for running backtests
    op.execute("""
        CREATE INDEX idx_backtests_running
        ON backtests (user_id, created_at DESC)
        WHERE status = 'RUNNING'
    """)

    # 8. backtests: Partial index for pending backtests
    op.execute("""
        CREATE INDEX idx_backtests_pending
        ON backtests (user_id, created_at DESC)
        WHERE status = 'PENDING'
    """)

    # 9. stocks: Active stocks filter (commonly used)
    op.execute("""
        CREATE INDEX idx_stocks_active_category
        ON stocks (category, market)
        WHERE is_active = 'active'
    """)


def downgrade() -> None:
    # Drop indexes in reverse order
    op.execute('DROP INDEX IF EXISTS idx_stocks_active_category')
    op.execute('DROP INDEX IF EXISTS idx_backtests_pending')
    op.execute('DROP INDEX IF EXISTS idx_backtests_running')
    op.drop_index('idx_trades_backtest_stock_date_desc', 'trades')
    op.drop_index('idx_fundamental_stock_indicator_date_desc', 'fundamental_data')
    op.drop_index('idx_minute_stock_timeframe_datetime_desc', 'stock_minute_prices')
    op.drop_index('idx_institutional_date_type', 'institutional_investors')
    op.drop_index('idx_institutional_stock_date_desc', 'institutional_investors')
    op.drop_index('idx_stock_prices_stock_date_desc', 'stock_prices')
