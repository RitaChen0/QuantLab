#!/usr/bin/env python3
"""
PCR Contrarian Strategy Example
選擇權 PCR 反向策略範例

策略邏輯：
- 當 PCR Volume > 1.2 時，市場過度看跌 → 做多
- 當 PCR Volume < 0.8 時，市場過度看漲 → 做空
- 使用選擇權因子預測標的物價格走勢

數據來源：
- 選擇權因子：來自 option_daily_factors 表
- 標的價格：來自 Qlib 二進制文件

適用範圍：
- 階段一：使用 PCR Volume 和 ATM IV
- 標的物：TX (台指期貨)、MTX (小台期貨)

使用方式：
```python
python examples/strategies/option_pcr_contrarian.py --symbol TX --start_date 2024-01-01 --end_date 2024-12-31
```
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import qlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

# Initialize Qlib
qlib.init(provider_uri='/data/qlib/tw_stock_v2')


class OptionPCRContrarian:
    """
    選擇權 PCR 反向策略

    參數：
    - pcr_high_threshold: PCR 高閾值（預設 1.2）
    - pcr_low_threshold: PCR 低閾值（預設 0.8）
    - holding_period: 持有期間（預設 5 日）
    - position_size: 部位大小（預設 1.0）
    """

    def __init__(
        self,
        pcr_high_threshold=1.2,
        pcr_low_threshold=0.8,
        holding_period=5,
        position_size=1.0
    ):
        self.pcr_high_threshold = pcr_high_threshold
        self.pcr_low_threshold = pcr_low_threshold
        self.holding_period = holding_period
        self.position_size = position_size

        logger.info(
            f"[PCR_STRATEGY] Initialized with thresholds: "
            f"High={pcr_high_threshold}, Low={pcr_low_threshold}"
        )

    def generate_signals(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        生成交易信號

        Args:
            symbol: 標的代碼（如 'TX', 'MTX'）
            start_date: 開始日期（YYYY-MM-DD）
            end_date: 結束日期（YYYY-MM-DD）

        Returns:
            DataFrame with columns: date, pcr, signal, position
        """
        logger.info(
            f"[PCR_STRATEGY] Generating signals for {symbol}: "
            f"{start_date} to {end_date}"
        )

        try:
            # 從 Qlib 讀取選擇權因子
            from qlib.data import D

            # 讀取 PCR 因子（$pcr 是在 export_option_to_qlib.py 中匯出的）
            fields = ['$close', '$pcr', '$atm_iv']

            logger.debug(f"[PCR_STRATEGY] Fetching data fields: {fields}")

            data = D.features(
                instruments=[symbol],
                fields=fields,
                start_time=start_date,
                end_time=end_date,
                freq='day'
            )

            if data.empty:
                logger.warning(f"[PCR_STRATEGY] No data found for {symbol}")
                return pd.DataFrame()

            # 重置索引，將 MultiIndex 轉為列
            data = data.reset_index()
            data.columns = ['date', 'symbol', 'close', 'pcr', 'atm_iv']

            logger.info(f"[PCR_STRATEGY] Loaded {len(data)} data points")

            # 生成交易信號
            signals = []

            for i, row in data.iterrows():
                pcr = row['pcr']

                # 檢查 PCR 是否有效
                if pd.isna(pcr):
                    signal = 0  # 無信號
                elif pcr > self.pcr_high_threshold:
                    signal = 1  # 做多（市場過度看跌）
                elif pcr < self.pcr_low_threshold:
                    signal = -1  # 做空（市場過度看漲）
                else:
                    signal = 0  # 中性

                signals.append({
                    'date': row['date'],
                    'close': row['close'],
                    'pcr': pcr,
                    'atm_iv': row['atm_iv'],
                    'signal': signal,
                    'position': signal * self.position_size
                })

            result_df = pd.DataFrame(signals)

            # 計算信號統計
            buy_signals = (result_df['signal'] == 1).sum()
            sell_signals = (result_df['signal'] == -1).sum()
            neutral_signals = (result_df['signal'] == 0).sum()

            logger.info(
                f"[PCR_STRATEGY] Signal statistics: "
                f"Buy={buy_signals}, Sell={sell_signals}, Neutral={neutral_signals}"
            )

            return result_df

        except Exception as e:
            logger.error(
                f"[PCR_STRATEGY] Error generating signals: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return pd.DataFrame()

    def backtest(self, signals_df: pd.DataFrame) -> dict:
        """
        簡單回測（未考慮交易成本）

        Args:
            signals_df: 信號 DataFrame

        Returns:
            回測結果統計
        """
        if signals_df.empty:
            logger.warning("[PCR_STRATEGY] No signals to backtest")
            return {}

        logger.info("[PCR_STRATEGY] Starting backtest...")

        # 計算每日收益
        signals_df['returns'] = signals_df['close'].pct_change()
        signals_df['strategy_returns'] = signals_df['position'].shift(1) * signals_df['returns']

        # 計算累積收益
        signals_df['cumulative_returns'] = (1 + signals_df['returns']).cumprod() - 1
        signals_df['cumulative_strategy_returns'] = (1 + signals_df['strategy_returns']).cumprod() - 1

        # 統計指標
        total_return = signals_df['cumulative_strategy_returns'].iloc[-1]
        buy_and_hold_return = signals_df['cumulative_returns'].iloc[-1]

        # 年化收益（假設 252 交易日）
        trading_days = len(signals_df)
        years = trading_days / 252
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Sharpe Ratio（假設無風險利率 = 0）
        sharpe_ratio = (
            signals_df['strategy_returns'].mean() / signals_df['strategy_returns'].std() * np.sqrt(252)
            if signals_df['strategy_returns'].std() > 0 else 0
        )

        # Maximum Drawdown
        cumulative = (1 + signals_df['strategy_returns']).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        # 勝率
        winning_trades = (signals_df['strategy_returns'] > 0).sum()
        total_trades = (signals_df['position'].shift(1) != 0).sum()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        results = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'buy_and_hold_return': buy_and_hold_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'trading_days': trading_days
        }

        logger.info(
            f"[PCR_STRATEGY] Backtest results:\n"
            f"  Total Return: {total_return*100:.2f}%\n"
            f"  Annualized Return: {annualized_return*100:.2f}%\n"
            f"  Buy & Hold Return: {buy_and_hold_return*100:.2f}%\n"
            f"  Sharpe Ratio: {sharpe_ratio:.2f}\n"
            f"  Max Drawdown: {max_drawdown*100:.2f}%\n"
            f"  Win Rate: {win_rate*100:.1f}%\n"
            f"  Total Trades: {total_trades}"
        )

        return results

    def plot_results(self, signals_df: pd.DataFrame, save_path: str = None):
        """
        繪製回測結果圖表

        Args:
            signals_df: 信號 DataFrame
            save_path: 儲存路徑（可選）
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

            # 圖 1：價格與信號
            ax1 = axes[0]
            ax1.plot(signals_df['date'], signals_df['close'], label='Close Price', color='black')

            # 標記買入信號
            buy_signals = signals_df[signals_df['signal'] == 1]
            ax1.scatter(
                buy_signals['date'], buy_signals['close'],
                marker='^', color='green', s=100, label='Buy Signal', zorder=5
            )

            # 標記賣出信號
            sell_signals = signals_df[signals_df['signal'] == -1]
            ax1.scatter(
                sell_signals['date'], sell_signals['close'],
                marker='v', color='red', s=100, label='Sell Signal', zorder=5
            )

            ax1.set_ylabel('Price')
            ax1.set_title('PCR Contrarian Strategy - Price & Signals')
            ax1.legend(loc='best')
            ax1.grid(True, alpha=0.3)

            # 圖 2：PCR 指標
            ax2 = axes[1]
            ax2.plot(signals_df['date'], signals_df['pcr'], label='PCR Volume', color='blue')
            ax2.axhline(y=self.pcr_high_threshold, color='red', linestyle='--', label=f'High Threshold ({self.pcr_high_threshold})')
            ax2.axhline(y=self.pcr_low_threshold, color='green', linestyle='--', label=f'Low Threshold ({self.pcr_low_threshold})')
            ax2.set_ylabel('PCR')
            ax2.set_title('Put/Call Ratio')
            ax2.legend(loc='best')
            ax2.grid(True, alpha=0.3)

            # 圖 3：累積收益
            ax3 = axes[2]
            ax3.plot(
                signals_df['date'],
                signals_df['cumulative_strategy_returns'] * 100,
                label='Strategy Return',
                color='blue'
            )
            ax3.plot(
                signals_df['date'],
                signals_df['cumulative_returns'] * 100,
                label='Buy & Hold Return',
                color='gray',
                alpha=0.7
            )
            ax3.set_xlabel('Date')
            ax3.set_ylabel('Cumulative Return (%)')
            ax3.set_title('Cumulative Returns Comparison')
            ax3.legend(loc='best')
            ax3.grid(True, alpha=0.3)

            # 格式化 x 軸日期
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"[PCR_STRATEGY] Chart saved to {save_path}")
            else:
                plt.show()

        except ImportError:
            logger.warning("[PCR_STRATEGY] matplotlib not available, skipping plot")
        except Exception as e:
            logger.error(f"[PCR_STRATEGY] Error plotting results: {str(e)}")


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description='PCR Contrarian Strategy Backtest')
    parser.add_argument('--symbol', type=str, default='TX', help='Symbol (default: TX)')
    parser.add_argument('--start_date', type=str, default='2024-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2024-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--pcr_high', type=float, default=1.2, help='PCR high threshold (default: 1.2)')
    parser.add_argument('--pcr_low', type=float, default=0.8, help='PCR low threshold (default: 0.8)')
    parser.add_argument('--save_chart', type=str, default=None, help='Save chart to file path')

    args = parser.parse_args()

    # 創建策略實例
    strategy = OptionPCRContrarian(
        pcr_high_threshold=args.pcr_high,
        pcr_low_threshold=args.pcr_low
    )

    # 生成信號
    signals_df = strategy.generate_signals(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date
    )

    if signals_df.empty:
        logger.error("[PCR_STRATEGY] No signals generated. Exiting.")
        return

    # 執行回測
    results = strategy.backtest(signals_df)

    # 繪製結果
    if results:
        strategy.plot_results(signals_df, save_path=args.save_chart)

    logger.info("[PCR_STRATEGY] Strategy analysis completed!")


if __name__ == '__main__':
    main()
