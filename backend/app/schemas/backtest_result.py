"""
BacktestResult-related Pydantic schemas for request/response validation
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# ============ Detailed Results Sub-schemas ============

class DailyNavPoint(BaseModel):
    """每日淨值數據點"""
    date: str = Field(..., description="日期 (YYYY-MM-DD)")
    value: float = Field(..., description="總淨值")
    cash: float = Field(..., description="現金")
    stock_value: float = Field(..., description="股票價值")


class MonthlyReturn(BaseModel):
    """月度報酬"""
    month: str = Field(..., description="月份 (YYYY-MM)")
    return_pct: float = Field(..., description="報酬率 (%)")


class RollingSharpePoint(BaseModel):
    """滾動夏普率數據點"""
    date: str = Field(..., description="日期")
    sharpe: float = Field(..., description="夏普率")


class DrawdownPoint(BaseModel):
    """回撤數據點"""
    date: str = Field(..., description="日期")
    drawdown_pct: float = Field(..., description="回撤百分比 (%)")


class TradeDistribution(BaseModel):
    """交易分佈統計"""
    profit_bins: List[int] = Field(default_factory=list, description="獲利分佈（直方圖）")
    loss_bins: List[int] = Field(default_factory=list, description="虧損分佈（直方圖）")
    holding_days_dist: Dict[str, int] = Field(default_factory=dict, description="持倉天數分佈")


class DetailedResults(BaseModel):
    """詳細回測結果（用於視覺化）"""
    daily_nav: Optional[List[DailyNavPoint]] = Field(None, description="每日淨值時間序列")
    monthly_returns: Optional[List[MonthlyReturn]] = Field(None, description="月度報酬")
    rolling_sharpe: Optional[List[RollingSharpePoint]] = Field(None, description="滾動夏普率")
    drawdown_series: Optional[List[DrawdownPoint]] = Field(None, description="回撤時間序列")
    trade_distribution: Optional[TradeDistribution] = Field(None, description="交易分佈統計")


# ============ BacktestResult Schemas ============

class BacktestResultBase(BaseModel):
    """Base backtest result schema with common fields"""
    # 基本績效指標
    total_return: Optional[Decimal] = Field(None, description="總報酬率（%）")
    annual_return: Optional[Decimal] = Field(None, description="年化報酬率（%）")
    final_portfolio_value: Optional[Decimal] = Field(None, description="最終資產淨值")

    # 風險指標
    sharpe_ratio: Optional[Decimal] = Field(None, description="夏普比率")
    max_drawdown: Optional[Decimal] = Field(None, description="最大回撤（%）")
    volatility: Optional[Decimal] = Field(None, description="波動率")

    # 交易統計
    total_trades: Optional[int] = Field(None, ge=0, description="總交易次數")
    winning_trades: Optional[int] = Field(None, ge=0, description="獲利交易次數")
    losing_trades: Optional[int] = Field(None, ge=0, description="虧損交易次數")
    win_rate: Optional[Decimal] = Field(None, description="勝率（%）")

    # 獲利統計
    average_profit: Optional[Decimal] = Field(None, description="平均獲利")
    average_loss: Optional[Decimal] = Field(None, description="平均虧損")
    profit_factor: Optional[Decimal] = Field(None, description="獲利因子")

    # 進階指標
    sortino_ratio: Optional[Decimal] = Field(None, description="索提諾比率")
    calmar_ratio: Optional[Decimal] = Field(None, description="卡瑪比率")
    information_ratio: Optional[Decimal] = Field(None, description="信息比率")

    # 詳細視覺化數據
    detailed_results: Optional[Dict[str, Any]] = Field(None, description="詳細回測數據（JSON）")


class BacktestResultCreate(BacktestResultBase):
    """Schema for creating backtest result"""
    backtest_id: int = Field(..., gt=0, description="回測 ID")


class BacktestResultUpdate(BacktestResultBase):
    """Schema for updating backtest result (all fields optional)"""
    pass


class BacktestResultInDB(BacktestResultBase):
    """Schema for backtest result as stored in database"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_id: int
    created_at: datetime
    updated_at: datetime


class BacktestResult(BacktestResultBase):
    """Schema for backtest result response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_id: int
    created_at: datetime


# Additional utility schemas
class PerformanceMetrics(BaseModel):
    """Performance metrics summary"""
    returns: Decimal = Field(..., description="總報酬率（%）")
    sharpe: Optional[Decimal] = Field(None, description="夏普比率")
    max_dd: Optional[Decimal] = Field(None, description="最大回撤（%）")
    win_rate: Optional[Decimal] = Field(None, description="勝率（%）")


class BacktestResultSummary(BaseModel):
    """Simplified backtest result summary"""
    backtest_id: int
    total_return: Optional[Decimal]
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Optional[Decimal]
    total_trades: Optional[int]
    win_rate: Optional[Decimal]
