"""
圖表生成器

使用 matplotlib 生成回測結果圖表，用於 Telegram 通知。
"""

import os
import tempfile
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # 使用非交互式後端，避免在無 GUI 環境報錯
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from loguru import logger

# 設定中文字體（支援繁體中文）
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft JhengHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False  # 解決負號顯示問題


class ChartGenerator:
    """圖表生成器基類"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化圖表生成器

        Args:
            output_dir: 輸出目錄，默認使用系統臨時目錄
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.output_dir = Path(tempfile.gettempdir()) / "quantlab_charts"
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_output_path(self, filename: str) -> str:
        """
        獲取輸出文件路徑

        Args:
            filename: 文件名

        Returns:
            完整文件路徑
        """
        return str(self.output_dir / filename)

    @staticmethod
    def cleanup_old_charts(days: int = 1):
        """
        清理舊圖表文件

        Args:
            days: 保留天數
        """
        temp_dir = Path(tempfile.gettempdir()) / "quantlab_charts"
        if not temp_dir.exists():
            return

        import time
        cutoff_time = time.time() - (days * 86400)

        for file in temp_dir.glob("*.png"):
            if file.stat().st_mtime < cutoff_time:
                try:
                    file.unlink()
                    logger.debug(f"Deleted old chart: {file}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file}: {e}")


class BacktestChartGenerator(ChartGenerator):
    """回測圖表生成器"""

    def generate_equity_curve(
        self,
        dates: List[datetime],
        portfolio_values: List[float],
        initial_capital: float,
        backtest_id: Optional[int] = None,
        title: str = "回測權益曲線"
    ) -> str:
        """
        生成權益曲線圖

        Args:
            dates: 日期列表
            portfolio_values: 組合價值列表
            initial_capital: 初始資金
            backtest_id: 回測 ID（用於文件命名）
            title: 圖表標題

        Returns:
            生成的圖片文件路徑
        """
        try:
            # 創建圖表
            fig, ax = plt.subplots(figsize=(12, 6), dpi=100)

            # 繪製權益曲線
            ax.plot(dates, portfolio_values, linewidth=2, color='#2196F3', label='組合價值')

            # 繪製初始資金基準線
            ax.axhline(y=initial_capital, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='初始資金')

            # 計算收益率並填充顏色
            returns = [(v - initial_capital) / initial_capital * 100 for v in portfolio_values]
            colors = ['green' if r >= 0 else 'red' for r in returns]

            # 填充盈虧區域
            ax.fill_between(
                dates,
                portfolio_values,
                initial_capital,
                alpha=0.2,
                color='green',
                where=[v >= initial_capital for v in portfolio_values]
            )
            ax.fill_between(
                dates,
                portfolio_values,
                initial_capital,
                alpha=0.2,
                color='red',
                where=[v < initial_capital for v in portfolio_values]
            )

            # 設置標題和標籤
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('組合價值 (NT$)', fontsize=12)

            # 格式化 Y 軸（貨幣格式）
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

            # 格式化 X 軸（日期）
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.xticks(rotation=45, ha='right')

            # 添加網格
            ax.grid(True, alpha=0.3, linestyle='--')

            # 添加圖例
            ax.legend(loc='upper left', fontsize=10)

            # 調整布局
            plt.tight_layout()

            # 保存圖表
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"equity_curve_{backtest_id or timestamp}.png"
            output_path = self._get_output_path(filename)

            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"✅ 權益曲線圖已生成: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ 生成權益曲線圖失敗: {str(e)}")
            plt.close('all')  # 確保清理所有圖表
            raise

    def generate_equity_curve_from_trades(
        self,
        trades_data: List[Dict[str, Any]],
        initial_capital: float,
        backtest_id: Optional[int] = None
    ) -> Optional[str]:
        """
        從交易記錄生成權益曲線圖

        Args:
            trades_data: 交易記錄列表 [{date, pnl, cumulative_pnl}, ...]
            initial_capital: 初始資金
            backtest_id: 回測 ID

        Returns:
            生成的圖片文件路徑，失敗返回 None
        """
        if not trades_data:
            logger.warning("交易記錄為空，無法生成權益曲線")
            return None

        try:
            # 提取日期和累計權益
            dates = [trade['date'] if isinstance(trade['date'], datetime) else datetime.fromisoformat(str(trade['date']))
                     for trade in trades_data]
            cumulative_pnl = [trade.get('cumulative_pnl', 0) for trade in trades_data]

            # 計算組合價值
            portfolio_values = [initial_capital + pnl for pnl in cumulative_pnl]

            # 生成圖表
            return self.generate_equity_curve(
                dates=dates,
                portfolio_values=portfolio_values,
                initial_capital=initial_capital,
                backtest_id=backtest_id,
                title="回測權益曲線"
            )

        except Exception as e:
            logger.error(f"❌ 從交易記錄生成權益曲線失敗: {str(e)}")
            return None

    def generate_metrics_summary(
        self,
        metrics: Dict[str, Any],
        backtest_id: Optional[int] = None
    ) -> str:
        """
        生成績效指標摘要圖

        Args:
            metrics: 績效指標字典
            backtest_id: 回測 ID

        Returns:
            生成的圖片文件路徑
        """
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10), dpi=100)

            # 1. 收益率柱狀圖
            total_return = metrics.get('total_return', 0) * 100
            ax1.bar(['總收益率'], [total_return], color='green' if total_return > 0 else 'red', alpha=0.7)
            ax1.set_ylabel('收益率 (%)', fontsize=10)
            ax1.set_title('總收益率', fontsize=12, fontweight='bold')
            ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax1.grid(True, alpha=0.3)

            # 2. 勝率和交易次數
            win_rate = metrics.get('win_rate', 0) * 100
            total_trades = metrics.get('total_trades', 0)
            ax2.bar(['勝率', '交易次數'], [win_rate, total_trades], color=['#4CAF50', '#2196F3'], alpha=0.7)
            ax2.set_ylabel('值', fontsize=10)
            ax2.set_title('勝率與交易次數', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)

            # 3. Sharpe 比率
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            color = 'green' if sharpe_ratio > 1 else 'orange' if sharpe_ratio > 0 else 'red'
            ax3.bar(['Sharpe 比率'], [sharpe_ratio], color=color, alpha=0.7)
            ax3.set_ylabel('Sharpe 比率', fontsize=10)
            ax3.set_title('Sharpe 比率', fontsize=12, fontweight='bold')
            ax3.axhline(y=1, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='良好基準')
            ax3.legend(fontsize=8)
            ax3.grid(True, alpha=0.3)

            # 4. 最大回撤
            max_drawdown = abs(metrics.get('max_drawdown', 0)) * 100
            ax4.bar(['最大回撤'], [-max_drawdown], color='red', alpha=0.7)
            ax4.set_ylabel('回撤 (%)', fontsize=10)
            ax4.set_title('最大回撤', fontsize=12, fontweight='bold')
            ax4.grid(True, alpha=0.3)

            # 調整布局
            plt.tight_layout()

            # 保存圖表
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_summary_{backtest_id or timestamp}.png"
            output_path = self._get_output_path(filename)

            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"✅ 績效摘要圖已生成: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ 生成績效摘要圖失敗: {str(e)}")
            plt.close('all')
            raise


# 全局實例
backtest_chart_generator = BacktestChartGenerator()
