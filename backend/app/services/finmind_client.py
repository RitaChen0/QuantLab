"""
FinMind API Client

整合 FinMind 開源金融資料 API，提供產業鏈等額外數據源。
官方文檔: https://finmind.github.io/
"""
import os
import requests
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from loguru import logger


class FinMindClient:
    """
    FinMind API 客戶端

    提供台股產業鏈、財務數據等功能。
    支援使用 API Token 訪問進階數據集。
    """

    BASE_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self):
        """初始化 FinMind 客戶端"""
        self.session = requests.Session()
        self.api_token = os.getenv("FINMIND_API_TOKEN", "")
        if self.api_token:
            logger.info("FinMind client initialized with API token")
        else:
            logger.warning("FinMind client initialized without API token (some datasets may be unavailable)")

    def _make_request(
        self,
        dataset: str,
        data_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        發送 API 請求

        Args:
            dataset: 數據集名稱
            data_id: 數據ID (如股票代號)
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            **kwargs: 其他參數

        Returns:
            DataFrame 格式的數據
        """
        params = {
            "dataset": dataset,
        }

        # 加入 API Token (如果有設定)
        if self.api_token:
            params["token"] = self.api_token

        if data_id:
            params["data_id"] = data_id

        if start_date:
            params["start_date"] = start_date

        if end_date:
            params["end_date"] = end_date

        # 添加其他參數
        params.update(kwargs)

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )

            # 先檢查 JSON 響應（FinMind 可能返回 400 但包含詳細訊息）
            data = response.json()

            if data.get("status") == 200:
                df = pd.DataFrame(data.get("data", []))
                logger.debug(f"FinMind API success: {dataset}, rows: {len(df)}")
                return df
            else:
                msg = data.get("msg", "Unknown error")
                logger.warning(f"FinMind API warning: {msg}")

                # 檢查是否為會員等級限制
                if "level" in msg.lower() and "register" in msg.lower():
                    raise Exception(
                        f"此數據集（{dataset}）需要 FinMind 付費會員才能訪問。\n"
                        f"當前會員等級：註冊會員（Register）\n"
                        f"請前往 https://finmindtrade.com/analysis/#/Sponsor/sponsor 升級會員。\n"
                        f"FinMind 原始訊息：{msg}"
                    )

                return pd.DataFrame()

        except requests.exceptions.Timeout as e:
            logger.error(f"FinMind API timeout: {str(e)}")
            raise Exception(f"FinMind API 請求超時（30秒），請稍後再試")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"FinMind API connection error: {str(e)}")
            raise Exception(f"無法連接到 FinMind API 伺服器，請檢查網絡連接")
        except requests.exceptions.HTTPError as e:
            logger.error(f"FinMind API HTTP error: {str(e)}")
            if e.response.status_code == 400:
                raise Exception(f"FinMind API 請求格式錯誤（400 Bad Request），可能需要 API Token 或數據集名稱有誤")
            elif e.response.status_code == 401:
                raise Exception(f"FinMind API 認證失敗（401 Unauthorized），請設定正確的 API Token")
            elif e.response.status_code == 404:
                raise Exception(f"FinMind API 端點不存在（404 Not Found），API 可能已變更")
            elif e.response.status_code >= 500:
                raise Exception(f"FinMind API 伺服器錯誤（{e.response.status_code}），請稍後再試")
            else:
                raise Exception(f"FinMind API 請求失敗（HTTP {e.response.status_code}）")
        except requests.exceptions.RequestException as e:
            logger.error(f"FinMind API request failed: {str(e)}")
            raise Exception(f"FinMind API 請求失敗：{str(e)}")
        except Exception as e:
            logger.error(f"FinMind API error: {str(e)}")
            raise

    # ========== 產業鏈數據 ==========

    def get_industry_chain(self) -> pd.DataFrame:
        """
        獲取台股產業鏈分類

        Returns:
            DataFrame with columns: stock_id, industry_chain
        """
        df = self._make_request(dataset="TaiwanStockIndustryChain")

        if not df.empty:
            logger.info(f"Retrieved {len(df)} industry chain records")

        return df

    def get_stocks_by_industry_chain(self, industry_chain: str) -> List[str]:
        """
        獲取特定產業鏈的所有股票

        Args:
            industry_chain: 產業鏈名稱

        Returns:
            股票代號列表
        """
        df = self.get_industry_chain()

        if df.empty:
            return []

        filtered = df[df['industry_chain'] == industry_chain]
        return filtered['stock_id'].tolist()

    def get_all_industry_chains(self) -> List[str]:
        """
        獲取所有產業鏈名稱

        Returns:
            產業鏈名稱列表
        """
        df = self.get_industry_chain()

        if df.empty:
            return []

        return df['industry_chain'].unique().tolist()

    # ========== 財務數據 ==========

    def get_financial_statement(
        self,
        stock_id: str,
        statement_type: str = "balance_sheet",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取財務報表

        Args:
            stock_id: 股票代號
            statement_type: 報表類型
                - balance_sheet: 資產負債表
                - income_statement: 損益表
                - cash_flow_statement: 現金流量表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            財務報表數據
        """
        dataset_map = {
            "balance_sheet": "TaiwanStockBalanceSheet",
            "income_statement": "TaiwanStockIncomeStatement",
            "cash_flow_statement": "TaiwanStockCashFlowsStatement"
        }

        dataset = dataset_map.get(statement_type, "TaiwanStockBalanceSheet")

        return self._make_request(
            dataset=dataset,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 股利數據 ==========

    def get_dividend(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取股利數據

        Args:
            stock_id: 股票代號
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            股利數據
        """
        return self._make_request(
            dataset="TaiwanStockDividend",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 月營收數據 ==========

    def get_monthly_revenue(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取月營收數據

        Args:
            stock_id: 股票代號
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            月營收數據
        """
        return self._make_request(
            dataset="TaiwanStockMonthRevenue",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 機構投資人買賣超 ==========

    def get_institutional_investors(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取三大法人買賣超

        Args:
            stock_id: 股票代號
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            法人買賣超數據
        """
        return self._make_request(
            dataset="TaiwanStockInstitutionalInvestorsBuySell",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 融資融券 ==========

    def get_margin_trading(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取融資融券數據

        Args:
            stock_id: 股票代號
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            融資融券數據
        """
        return self._make_request(
            dataset="TaiwanStockMarginPurchaseShortSale",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 產業鏈聚合分析 ==========

    def get_industry_chain_summary(self, industry_chain: str) -> Dict[str, Any]:
        """
        獲取產業鏈摘要統計

        Args:
            industry_chain: 產業鏈名稱

        Returns:
            產業鏈摘要信息
        """
        stocks = self.get_stocks_by_industry_chain(industry_chain)

        return {
            "industry_chain": industry_chain,
            "stocks_count": len(stocks),
            "stocks": stocks,
            "timestamp": datetime.now().isoformat()
        }

    # ========== 工具方法 ==========

    @staticmethod
    def get_available_datasets() -> List[str]:
        """
        獲取可用的數據集列表

        Returns:
            數據集名稱列表
        """
        return [
            "TaiwanStockInfo",
            "TaiwanStockPrice",
            "TaiwanStockIndustryChain",
            "TaiwanStockBalanceSheet",
            "TaiwanStockIncomeStatement",
            "TaiwanStockCashFlowsStatement",
            "TaiwanStockDividend",
            "TaiwanStockMonthRevenue",
            "TaiwanStockInstitutionalInvestors",
            "TaiwanStockMarginPurchaseShortSale",
            "TaiwanStockPER",
            "TaiwanStockPBR"
        ]


# 使用範例
if __name__ == "__main__":
    client = FinMindClient()

    # 獲取產業鏈
    chains = client.get_all_industry_chains()
    print(f"Total industry chains: {len(chains)}")
    print(f"Industry chains: {chains[:10]}")

    # 獲取特定產業鏈的股票
    if chains:
        stocks = client.get_stocks_by_industry_chain(chains[0])
        print(f"\nStocks in {chains[0]}: {len(stocks)}")
        print(f"Sample stocks: {stocks[:5]}")
