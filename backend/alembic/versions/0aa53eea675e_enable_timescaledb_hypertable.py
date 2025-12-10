"""enable_timescaledb_hypertable

Revision ID: 0aa53eea675e
Revises: 430c1561c808
Create Date: 2025-12-01 13:21:11.345936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0aa53eea675e'
down_revision: Union[str, None] = '430c1561c808'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable TimescaleDB extension and convert stock_prices to hypertable"""

    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # Convert stock_prices table to hypertable
    # Partitioned by 'date' column with 7-day chunks
    op.execute("""
        SELECT create_hypertable(
            'stock_prices',
            'date',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)

    # Create compression policy for data older than 30 days
    op.execute("""
        ALTER TABLE stock_prices SET (
            timescaledb.compress,
            timescaledb.compress_orderby = 'date DESC',
            timescaledb.compress_segmentby = 'stock_id'
        );
    """)

    op.execute("""
        SELECT add_compression_policy('stock_prices', INTERVAL '30 days', if_not_exists => TRUE);
    """)


def downgrade() -> None:
    """Disable TimescaleDB hypertable"""

    # Remove compression policy
    op.execute("""
        SELECT remove_compression_policy('stock_prices', if_exists => TRUE);
    """)

    # Note: Cannot easily revert hypertable to regular table
    # This is a one-way migration for production use
    # In development, you can drop and recreate the table
    pass
