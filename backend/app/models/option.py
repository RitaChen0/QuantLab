"""
Option Models

選擇權相關資料表模型，支援三階段演進式架構：
- 階段一：基礎設施 + 聚合因子（PCR, ATM IV）
- 階段二：分鐘線 + IV 曲面
- 階段三：Greeks + 高級策略
"""
from sqlalchemy import (
    Column, String, TIMESTAMP, Numeric, BigInteger, Integer, Date, DateTime,
    Index, PrimaryKeyConstraint, ForeignKey, CheckConstraint, text
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class OptionContract(Base):
    """
    選擇權合約主表

    用途：儲存選擇權合約基本資訊（類似期貨的 stocks 表）
    階段：一（完整建立，為未來擴展預留欄位）

    範例：TXO202512C23000 (台指選擇權 2025年12月 Call 23000)
    """
    __tablename__ = "option_contracts"

    # 主鍵
    contract_id = Column(
        String(20),
        primary_key=True,
        index=True,
        comment="合約代碼（如 TXO202512C23000）"
    )

    # 基本資訊（階段一使用）
    underlying_id = Column(
        String(10),
        ForeignKey("stocks.stock_id"),
        nullable=False,
        comment="標的物代碼（如 TX202512、2330）"
    )
    underlying_type = Column(
        String(10),
        nullable=False,
        comment="標的物類型（STOCK/FUTURES）"
    )
    option_type = Column(
        String(4),
        nullable=False,
        comment="選擇權類型（CALL/PUT）"
    )
    strike_price = Column(
        Numeric(10, 2),
        nullable=False,
        comment="履約價格"
    )
    expiry_date = Column(
        Date,
        nullable=False,
        comment="到期日"
    )

    # 合約狀態
    is_active = Column(
        String(10),
        default='active',
        nullable=False,
        comment="狀態（active/expired/exercised）"
    )
    settlement_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="結算價格（階段一可 NULL，階段三填充）"
    )

    # 合約規格（階段二擴展）
    contract_size = Column(
        Integer,
        default=1,
        nullable=True,
        comment="合約乘數"
    )
    tick_size = Column(
        Numeric(6, 4),
        nullable=True,
        comment="最小跳動單位"
    )

    # 時間戳
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # 關聯
    underlying = relationship("Stock")

    # 表設定
    __table_args__ = (
        CheckConstraint(
            "option_type IN ('CALL', 'PUT')",
            name='ck_option_type'
        ),
        CheckConstraint(
            "underlying_type IN ('STOCK', 'FUTURES')",
            name='ck_underlying_type'
        ),
        CheckConstraint(
            "is_active IN ('active', 'expired', 'exercised')",
            name='ck_is_active'
        ),
        Index('idx_option_underlying', 'underlying_id'),
        Index('idx_option_expiry', 'expiry_date'),
        Index('idx_option_active', 'is_active'),
        Index('idx_option_type_strike', 'option_type', 'strike_price'),
        Index('idx_option_underlying_expiry', 'underlying_id', 'expiry_date'),
        {'comment': '選擇權合約主表（支援演進式架構）'}
    )

    def __repr__(self):
        return f"<OptionContract(contract_id={self.contract_id}, type={self.option_type}, strike={self.strike_price})>"


class OptionDailyFactor(Base):
    """
    選擇權每日聚合因子

    用途：儲存每日計算的選擇權因子，供 Qlib 策略使用
    演進：階段一 3 欄位 → 階段二 +5 欄位 → 階段三 +Greeks 摘要

    階段一因子：pcr_volume, pcr_open_interest, atm_iv
    階段二因子：iv_skew, iv_term_structure, max_pain_strike
    階段三因子：avg_call_delta, avg_put_delta, gamma_exposure
    """
    __tablename__ = "option_daily_factors"

    # 複合主鍵
    underlying_id = Column(
        String(10),
        ForeignKey("stocks.stock_id"),
        nullable=False,
        comment="標的物代碼"
    )
    date = Column(
        Date,
        nullable=False,
        comment="資料日期"
    )

    # ========== 階段一：基礎因子（必填） ==========
    pcr_volume = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Put/Call Ratio (成交量)"
    )
    pcr_open_interest = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Put/Call Ratio (未平倉量)"
    )
    atm_iv = Column(
        Numeric(8, 6),
        nullable=True,
        comment="ATM 隱含波動率"
    )

    # ========== 階段二：進階因子（可 NULL） ==========
    iv_skew = Column(
        Numeric(8, 6),
        nullable=True,
        comment="IV Skew (25 Delta)"
    )
    iv_term_structure = Column(
        Numeric(8, 6),
        nullable=True,
        comment="近月/遠月 IV 比值"
    )
    max_pain_strike = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Max Pain 履約價"
    )
    total_call_oi = Column(
        BigInteger,
        nullable=True,
        comment="Call 總未平倉量"
    )
    total_put_oi = Column(
        BigInteger,
        nullable=True,
        comment="Put 總未平倉量"
    )

    # ========== 階段三：Greeks 摘要（可 NULL） ==========
    avg_call_delta = Column(
        Numeric(8, 6),
        nullable=True,
        comment="ATM Call Delta 均值"
    )
    avg_put_delta = Column(
        Numeric(8, 6),
        nullable=True,
        comment="ATM Put Delta 均值"
    )
    gamma_exposure = Column(
        Numeric(16, 2),
        nullable=True,
        comment="Gamma 總曝險"
    )
    vanna_exposure = Column(
        Numeric(16, 2),
        nullable=True,
        comment="Vanna 曝險"
    )

    # 元數據
    data_quality_score = Column(
        Numeric(3, 2),
        nullable=True,
        comment="資料品質評分 (0-1)"
    )
    calculation_version = Column(
        String(10),
        nullable=True,
        comment="計算版本（用於回測一致性）"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # 關聯
    underlying = relationship(
        "Stock",
        back_populates="option_daily_factors"
    )

    # 表設定
    __table_args__ = (
        PrimaryKeyConstraint('underlying_id', 'date', name='pk_option_daily_factors'),
        Index('idx_option_factors_date', 'date'),
        Index('idx_option_factors_underlying_date', 'underlying_id', 'date'),
        {'comment': '選擇權每日聚合因子（支援三階段演進）'}
    )

    def __repr__(self):
        return f"<OptionDailyFactor(underlying={self.underlying_id}, date={self.date}, pcr={self.pcr_volume})>"


class OptionMinutePrice(Base):
    """
    選擇權分鐘線價格

    用途：儲存選擇權分鐘級 OHLCV 資料
    階段：二（啟用）
    策略：獨立表，使用 TimescaleDB hypertable

    注意：階段一暫不使用，預留結構
    """
    __tablename__ = "option_minute_prices"

    # 複合主鍵
    contract_id = Column(
        String(20),
        ForeignKey("option_contracts.contract_id"),
        nullable=False,
        comment="合約代碼"
    )
    datetime = Column(
        TIMESTAMP,
        nullable=False,
        comment="時間戳記"
    )

    # OHLCV
    open = Column(
        Numeric(10, 2),
        nullable=False,
        comment="開盤價"
    )
    high = Column(
        Numeric(10, 2),
        nullable=False,
        comment="最高價"
    )
    low = Column(
        Numeric(10, 2),
        nullable=False,
        comment="最低價"
    )
    close = Column(
        Numeric(10, 2),
        nullable=False,
        comment="收盤價"
    )
    volume = Column(
        BigInteger,
        nullable=False,
        comment="成交量"
    )

    # 選擇權特有（階段二擴展）
    open_interest = Column(
        BigInteger,
        nullable=True,
        comment="未平倉量"
    )
    bid_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="買價"
    )
    ask_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="賣價"
    )

    # 隱含波動率（階段三計算）
    implied_volatility = Column(
        Numeric(8, 6),
        nullable=True,
        comment="隱含波動率"
    )

    # 關聯
    contract = relationship("OptionContract")

    # 表設定（TimescaleDB hypertable 由遷移腳本建立）
    __table_args__ = (
        PrimaryKeyConstraint('contract_id', 'datetime', name='pk_option_minute_prices'),
        Index('idx_option_minute_datetime', 'datetime'),
        Index('idx_option_minute_contract_datetime', 'contract_id', 'datetime'),
        {'comment': '選擇權分鐘線價格（TimescaleDB hypertable，階段二啟用）'}
    )

    def __repr__(self):
        return f"<OptionMinutePrice(contract={self.contract_id}, datetime={self.datetime}, close={self.close})>"


class OptionGreeks(Base):
    """
    選擇權 Greeks 時間序列

    用途：儲存 Greeks 五寶（Delta, Gamma, Theta, Vega, Rho）
    階段：三（啟用）

    注意：階段一、二暫不使用，預留結構
    """
    __tablename__ = "option_greeks"

    # 複合主鍵
    contract_id = Column(
        String(20),
        ForeignKey("option_contracts.contract_id"),
        nullable=False,
        comment="合約代碼"
    )
    datetime = Column(
        TIMESTAMP,
        nullable=False,
        comment="時間戳記"
    )

    # Greeks 五寶
    delta = Column(
        Numeric(8, 6),
        nullable=True,
        comment="Delta (對標的價格敏感度)"
    )
    gamma = Column(
        Numeric(8, 6),
        nullable=True,
        comment="Gamma (Delta 變化率)"
    )
    theta = Column(
        Numeric(8, 6),
        nullable=True,
        comment="Theta (時間價值衰減)"
    )
    vega = Column(
        Numeric(8, 6),
        nullable=True,
        comment="Vega (對波動率敏感度)"
    )
    rho = Column(
        Numeric(8, 6),
        nullable=True,
        comment="Rho (對利率敏感度)"
    )

    # 二階 Greeks（進階）
    vanna = Column(
        Numeric(10, 8),
        nullable=True,
        comment="Vanna (∂Delta/∂σ)"
    )
    charm = Column(
        Numeric(10, 8),
        nullable=True,
        comment="Charm (∂Delta/∂t)"
    )

    # 計算參數（可複現性）
    spot_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="計算時標的價格"
    )
    volatility = Column(
        Numeric(8, 6),
        nullable=True,
        comment="使用的波動率"
    )
    risk_free_rate = Column(
        Numeric(6, 4),
        nullable=True,
        comment="無風險利率"
    )

    # 關聯
    contract = relationship("OptionContract")

    # 表設定（TimescaleDB hypertable 由遷移腳本建立）
    __table_args__ = (
        PrimaryKeyConstraint('contract_id', 'datetime', name='pk_option_greeks'),
        Index('idx_option_greeks_datetime', 'datetime'),
        Index('idx_option_greeks_contract_datetime', 'contract_id', 'datetime'),
        {'comment': '選擇權 Greeks 時間序列（TimescaleDB hypertable，階段三啟用）'}
    )

    def __repr__(self):
        return f"<OptionGreeks(contract={self.contract_id}, datetime={self.datetime}, delta={self.delta})>"


class OptionSyncConfig(Base):
    """
    選擇權同步配置表

    用途：階段控制與功能開關

    關鍵配置：
    - stage: 當前階段（1/2/3）
    - enabled_underlyings: 啟用的標的物（TX,MTX）
    - sync_minute_data: 是否同步分鐘線（階段二）
    - calculate_greeks: 是否計算 Greeks（階段三）
    """
    __tablename__ = "option_sync_config"

    key = Column(
        String(50),
        primary_key=True,
        comment="配置鍵"
    )
    value = Column(
        String(500),
        nullable=True,
        comment="配置值"
    )
    description = Column(
        String(500),
        nullable=True,
        comment="說明"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # 表設定
    __table_args__ = (
        {'comment': '選擇權同步配置表（階段控制與功能開關）'}
    )

    def __repr__(self):
        return f"<OptionSyncConfig(key={self.key}, value={self.value})>"
