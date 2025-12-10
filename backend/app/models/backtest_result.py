from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class BacktestResult(Base):
    """回測績效結果模型"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, unique=True)

    # 基本績效指標
    total_return = Column(Numeric(10, 4), nullable=True, comment="總報酬率（%）")
    annual_return = Column(Numeric(10, 4), nullable=True, comment="年化報酬率（%）")
    final_portfolio_value = Column(Numeric(15, 2), nullable=True, comment="最終資產淨值")

    # 風險指標
    sharpe_ratio = Column(Numeric(10, 4), nullable=True, comment="夏普比率")
    max_drawdown = Column(Numeric(10, 4), nullable=True, comment="最大回撤（%）")
    volatility = Column(Numeric(10, 4), nullable=True, comment="波動率（標準差）")

    # 交易統計
    total_trades = Column(Integer, nullable=True, comment="總交易次數")
    winning_trades = Column(Integer, nullable=True, comment="獲利交易次數")
    losing_trades = Column(Integer, nullable=True, comment="虧損交易次數")
    win_rate = Column(Numeric(10, 4), nullable=True, comment="勝率（%）")

    # 獲利統計
    average_profit = Column(Numeric(15, 2), nullable=True, comment="平均獲利")
    average_loss = Column(Numeric(15, 2), nullable=True, comment="平均虧損")
    profit_factor = Column(Numeric(10, 4), nullable=True, comment="獲利因子（總獲利/總虧損）")

    # 進階指標
    sortino_ratio = Column(Numeric(10, 4), nullable=True, comment="索提諾比率")
    calmar_ratio = Column(Numeric(10, 4), nullable=True, comment="卡瑪比率")
    information_ratio = Column(Numeric(10, 4), nullable=True, comment="信息比率")

    # 詳細視覺化數據（JSON）
    detailed_results = Column(
        JSON,
        nullable=True,
        comment="詳細回測數據（用於視覺化）：daily_nav, monthly_returns, rolling_sharpe, trade_distribution, drawdown_series"
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    backtest = relationship("Backtest", back_populates="result")

    def __repr__(self):
        return f"<BacktestResult(id={self.id}, backtest_id={self.backtest_id}, total_return={self.total_return}%)>"
