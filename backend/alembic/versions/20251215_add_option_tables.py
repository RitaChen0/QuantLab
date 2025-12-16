"""add option tables for stage 1

Revision ID: 20251215_option
Revises: 14b5df59adf4
Create Date: 2025-12-15 12:00:00.000000

Creates option-related tables with evolution support:
- option_contracts: 選擇權合約主表
- option_daily_factors: 每日聚合因子（支援三階段演進）
- option_minute_prices: 分鐘線價格（階段二啟用）
- option_greeks: Greeks 時間序列（階段三啟用）
- option_sync_config: 同步配置表
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251215_option'
down_revision = '14b5df59adf4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==================== 1. option_contracts ====================
    op.create_table(
        'option_contracts',
        sa.Column('contract_id', sa.String(20), nullable=False, comment='合約代碼（如 TXO202512C23000）'),
        sa.Column('underlying_id', sa.String(10), nullable=False, comment='標的物代碼（如 TX202512、2330）'),
        sa.Column('underlying_type', sa.String(10), nullable=False, comment='標的物類型（STOCK/FUTURES）'),
        sa.Column('option_type', sa.String(4), nullable=False, comment='選擇權類型（CALL/PUT）'),
        sa.Column('strike_price', sa.Numeric(10, 2), nullable=False, comment='履約價格'),
        sa.Column('expiry_date', sa.Date(), nullable=False, comment='到期日'),
        sa.Column('is_active', sa.String(10), nullable=False, server_default='active', comment='狀態（active/expired/exercised）'),
        sa.Column('settlement_price', sa.Numeric(10, 2), nullable=True, comment='結算價格'),
        sa.Column('contract_size', sa.Integer(), nullable=True, server_default='1', comment='合約乘數'),
        sa.Column('tick_size', sa.Numeric(6, 4), nullable=True, comment='最小跳動單位'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('contract_id'),
        sa.ForeignKeyConstraint(['underlying_id'], ['stocks.stock_id'], ondelete='CASCADE'),
        sa.CheckConstraint("option_type IN ('CALL', 'PUT')", name='ck_option_type'),
        sa.CheckConstraint("underlying_type IN ('STOCK', 'FUTURES')", name='ck_underlying_type'),
        sa.CheckConstraint("is_active IN ('active', 'expired', 'exercised')", name='ck_is_active'),
        comment='選擇權合約主表（支援演進式架構）'
    )

    # 索引
    op.create_index('idx_option_underlying', 'option_contracts', ['underlying_id'])
    op.create_index('idx_option_expiry', 'option_contracts', ['expiry_date'])
    op.create_index('idx_option_active', 'option_contracts', ['is_active'])
    op.create_index('idx_option_type_strike', 'option_contracts', ['option_type', 'strike_price'])
    op.create_index('idx_option_underlying_expiry', 'option_contracts', ['underlying_id', 'expiry_date'])

    # ==================== 2. option_daily_factors ====================
    op.create_table(
        'option_daily_factors',
        sa.Column('underlying_id', sa.String(10), nullable=False, comment='標的物代碼'),
        sa.Column('date', sa.Date(), nullable=False, comment='資料日期'),

        # 階段一：基礎因子
        sa.Column('pcr_volume', sa.Numeric(10, 6), nullable=True, comment='Put/Call Ratio (成交量)'),
        sa.Column('pcr_open_interest', sa.Numeric(10, 6), nullable=True, comment='Put/Call Ratio (未平倉量)'),
        sa.Column('atm_iv', sa.Numeric(8, 6), nullable=True, comment='ATM 隱含波動率'),

        # 階段二：進階因子
        sa.Column('iv_skew', sa.Numeric(8, 6), nullable=True, comment='IV Skew (25 Delta)'),
        sa.Column('iv_term_structure', sa.Numeric(8, 6), nullable=True, comment='近月/遠月 IV 比值'),
        sa.Column('max_pain_strike', sa.Numeric(10, 2), nullable=True, comment='Max Pain 履約價'),
        sa.Column('total_call_oi', sa.BigInteger(), nullable=True, comment='Call 總未平倉量'),
        sa.Column('total_put_oi', sa.BigInteger(), nullable=True, comment='Put 總未平倉量'),

        # 階段三：Greeks 摘要
        sa.Column('avg_call_delta', sa.Numeric(8, 6), nullable=True, comment='ATM Call Delta 均值'),
        sa.Column('avg_put_delta', sa.Numeric(8, 6), nullable=True, comment='ATM Put Delta 均值'),
        sa.Column('gamma_exposure', sa.Numeric(16, 2), nullable=True, comment='Gamma 總曝險'),
        sa.Column('vanna_exposure', sa.Numeric(16, 2), nullable=True, comment='Vanna 曝險'),

        # 元數據
        sa.Column('data_quality_score', sa.Numeric(3, 2), nullable=True, comment='資料品質評分 (0-1)'),
        sa.Column('calculation_version', sa.String(10), nullable=True, comment='計算版本'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('underlying_id', 'date', name='pk_option_daily_factors'),
        sa.ForeignKeyConstraint(['underlying_id'], ['stocks.stock_id'], ondelete='CASCADE'),
        comment='選擇權每日聚合因子（支援三階段演進）'
    )

    # 索引
    op.create_index('idx_option_factors_date', 'option_daily_factors', ['date'])
    op.create_index('idx_option_factors_underlying_date', 'option_daily_factors', ['underlying_id', 'date'])

    # ==================== 3. option_minute_prices ====================
    # 階段二啟用，階段一先創建表結構
    op.create_table(
        'option_minute_prices',
        sa.Column('contract_id', sa.String(20), nullable=False, comment='合約代碼'),
        sa.Column('datetime', sa.TIMESTAMP(), nullable=False, comment='時間戳記'),

        # OHLCV
        sa.Column('open', sa.Numeric(10, 2), nullable=False, comment='開盤價'),
        sa.Column('high', sa.Numeric(10, 2), nullable=False, comment='最高價'),
        sa.Column('low', sa.Numeric(10, 2), nullable=False, comment='最低價'),
        sa.Column('close', sa.Numeric(10, 2), nullable=False, comment='收盤價'),
        sa.Column('volume', sa.BigInteger(), nullable=False, comment='成交量'),

        # 選擇權特有
        sa.Column('open_interest', sa.BigInteger(), nullable=True, comment='未平倉量'),
        sa.Column('bid_price', sa.Numeric(10, 2), nullable=True, comment='買價'),
        sa.Column('ask_price', sa.Numeric(10, 2), nullable=True, comment='賣價'),
        sa.Column('implied_volatility', sa.Numeric(8, 6), nullable=True, comment='隱含波動率'),

        sa.PrimaryKeyConstraint('contract_id', 'datetime', name='pk_option_minute_prices'),
        sa.ForeignKeyConstraint(['contract_id'], ['option_contracts.contract_id'], ondelete='CASCADE'),
        comment='選擇權分鐘線價格（TimescaleDB hypertable，階段二啟用）'
    )

    # 索引
    op.create_index('idx_option_minute_datetime', 'option_minute_prices', ['datetime'])
    op.create_index('idx_option_minute_contract_datetime', 'option_minute_prices', ['contract_id', 'datetime'])

    # ==================== 4. option_greeks ====================
    # 階段三啟用，階段一先創建表結構
    op.create_table(
        'option_greeks',
        sa.Column('contract_id', sa.String(20), nullable=False, comment='合約代碼'),
        sa.Column('datetime', sa.TIMESTAMP(), nullable=False, comment='時間戳記'),

        # Greeks 五寶
        sa.Column('delta', sa.Numeric(8, 6), nullable=True, comment='Delta (對標的價格敏感度)'),
        sa.Column('gamma', sa.Numeric(8, 6), nullable=True, comment='Gamma (Delta 變化率)'),
        sa.Column('theta', sa.Numeric(8, 6), nullable=True, comment='Theta (時間價值衰減)'),
        sa.Column('vega', sa.Numeric(8, 6), nullable=True, comment='Vega (對波動率敏感度)'),
        sa.Column('rho', sa.Numeric(8, 6), nullable=True, comment='Rho (對利率敏感度)'),

        # 二階 Greeks
        sa.Column('vanna', sa.Numeric(10, 8), nullable=True, comment='Vanna (∂Delta/∂σ)'),
        sa.Column('charm', sa.Numeric(10, 8), nullable=True, comment='Charm (∂Delta/∂t)'),

        # 計算參數
        sa.Column('spot_price', sa.Numeric(10, 2), nullable=True, comment='計算時標的價格'),
        sa.Column('volatility', sa.Numeric(8, 6), nullable=True, comment='使用的波動率'),
        sa.Column('risk_free_rate', sa.Numeric(6, 4), nullable=True, comment='無風險利率'),

        sa.PrimaryKeyConstraint('contract_id', 'datetime', name='pk_option_greeks'),
        sa.ForeignKeyConstraint(['contract_id'], ['option_contracts.contract_id'], ondelete='CASCADE'),
        comment='選擇權 Greeks 時間序列（TimescaleDB hypertable，階段三啟用）'
    )

    # 索引
    op.create_index('idx_option_greeks_datetime', 'option_greeks', ['datetime'])
    op.create_index('idx_option_greeks_contract_datetime', 'option_greeks', ['contract_id', 'datetime'])

    # ==================== 5. option_sync_config ====================
    op.create_table(
        'option_sync_config',
        sa.Column('key', sa.String(50), nullable=False, comment='配置鍵'),
        sa.Column('value', sa.String(500), nullable=True, comment='配置值'),
        sa.Column('description', sa.String(500), nullable=True, comment='說明'),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('key'),
        comment='選擇權同步配置表（階段控制與功能開關）'
    )

    # 插入默認配置
    op.execute("""
        INSERT INTO option_sync_config (key, value, description) VALUES
        ('stage', '1', '當前階段：1=基礎因子, 2=分鐘線, 3=Greeks'),
        ('enabled_underlyings', 'TX,MTX', '啟用的標的物'),
        ('sync_minute_data', 'false', '是否同步分鐘線（階段二）'),
        ('calculate_greeks', 'false', '是否計算 Greeks（階段三）'),
        ('retention_months', '6', '資料保留月數'),
        ('top_n_stocks', '50', 'Top N 股票選擇權')
    """)

    # ==================== 6. TimescaleDB Hypertables ====================
    # 將 option_minute_prices 和 option_greeks 轉換為 hypertable（階段二/三啟用）
    # 注意：階段一不執行，預留給階段二
    # op.execute("SELECT create_hypertable('option_minute_prices', 'datetime', if_not_exists => TRUE);")
    # op.execute("SELECT create_hypertable('option_greeks', 'datetime', if_not_exists => TRUE);")


def downgrade() -> None:
    # 刪除表（逆序）
    op.drop_table('option_sync_config')

    # 刪除 option_greeks
    op.drop_index('idx_option_greeks_contract_datetime', table_name='option_greeks')
    op.drop_index('idx_option_greeks_datetime', table_name='option_greeks')
    op.drop_table('option_greeks')

    # 刪除 option_minute_prices
    op.drop_index('idx_option_minute_contract_datetime', table_name='option_minute_prices')
    op.drop_index('idx_option_minute_datetime', table_name='option_minute_prices')
    op.drop_table('option_minute_prices')

    # 刪除 option_daily_factors
    op.drop_index('idx_option_factors_underlying_date', table_name='option_daily_factors')
    op.drop_index('idx_option_factors_date', table_name='option_daily_factors')
    op.drop_table('option_daily_factors')

    # 刪除 option_contracts
    op.drop_index('idx_option_underlying_expiry', table_name='option_contracts')
    op.drop_index('idx_option_type_strike', table_name='option_contracts')
    op.drop_index('idx_option_active', table_name='option_contracts')
    op.drop_index('idx_option_expiry', table_name='option_contracts')
    op.drop_index('idx_option_underlying', table_name='option_contracts')
    op.drop_table('option_contracts')
