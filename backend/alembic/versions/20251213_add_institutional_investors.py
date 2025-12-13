"""add institutional investors table

Revision ID: 20251213_inst_inv
Revises: a1b2c3d4e5f6
Create Date: 2025-12-13 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251213_inst_inv'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 創建法人買賣超資料表
    op.create_table(
        'institutional_investors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('stock_id', sa.String(10), nullable=False),
        sa.Column('investor_type', sa.String(50), nullable=False),
        sa.Column('buy_volume', sa.BigInteger(), nullable=False),
        sa.Column('sell_volume', sa.BigInteger(), nullable=False),
        sa.Column('net_buy_sell', sa.BigInteger(), sa.Computed('buy_volume - sell_volume'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', 'stock_id', 'investor_type', name='uq_institutional_date_stock_type'),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.stock_id'], ondelete='CASCADE')
    )

    # 創建索引以加速查詢
    op.create_index('idx_institutional_date', 'institutional_investors', ['date'])
    op.create_index('idx_institutional_stock_id', 'institutional_investors', ['stock_id'])
    op.create_index('idx_institutional_date_stock', 'institutional_investors', ['date', 'stock_id'])
    op.create_index('idx_institutional_stock_date', 'institutional_investors', ['stock_id', 'date'])
    op.create_index('idx_institutional_type', 'institutional_investors', ['investor_type'])


def downgrade() -> None:
    # 刪除索引
    op.drop_index('idx_institutional_type', table_name='institutional_investors')
    op.drop_index('idx_institutional_stock_date', table_name='institutional_investors')
    op.drop_index('idx_institutional_date_stock', table_name='institutional_investors')
    op.drop_index('idx_institutional_stock_id', table_name='institutional_investors')
    op.drop_index('idx_institutional_date', table_name='institutional_investors')

    # 刪除資料表
    op.drop_table('institutional_investors')
