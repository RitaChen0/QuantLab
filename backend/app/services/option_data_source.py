"""
Option Data Source

選擇權資料源抽象層，支援三階段演進：
- 階段一：每日收盤快照（計算 PCR、ATM IV）
- 階段二：分鐘線數據（計算 IV Skew、Max Pain）
- 階段三：Tick 數據（即時 Greeks 計算）
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import pandas as pd
from loguru import logger


class OptionDataSource(ABC):
    """選擇權資料源抽象基類"""

    @abstractmethod
    def get_option_chain(
        self,
        underlying: str,
        date: date
    ) -> pd.DataFrame:
        """
        獲取選擇權鏈（特定標的的所有合約）

        Args:
            underlying: 標的代碼（如 'TX', '2330'）
            date: 資料日期

        Returns:
            DataFrame with columns:
                - contract_id: 合約代碼
                - underlying_id: 標的代碼
                - option_type: CALL/PUT
                - strike_price: 履約價
                - expiry_date: 到期日
                - close: 收盤價
                - volume: 成交量
                - open_interest: 未平倉量（階段一可選）
        """
        pass

    @abstractmethod
    def get_minute_kbars(
        self,
        contract_id: str,
        start: date,
        end: date
    ) -> pd.DataFrame:
        """
        獲取選擇權分鐘線（階段二）

        Args:
            contract_id: 合約代碼
            start: 開始日期
            end: 結束日期

        Returns:
            DataFrame with OHLCV columns
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """檢查資料源是否可用"""
        pass


class ShioajiOptionDataSource(OptionDataSource):
    """
    Shioaji 選擇權資料源實作

    階段一：獲取每日收盤快照
    階段二：獲取分鐘線數據
    階段三：獲取 Tick 數據
    """

    def __init__(self, shioaji_client):
        """
        初始化

        Args:
            shioaji_client: ShioajiClient 實例
        """
        self.client = shioaji_client
        self._api = shioaji_client._api if shioaji_client else None

    def is_available(self) -> bool:
        """檢查 Shioaji 客戶端是否可用"""
        return self.client and self.client.is_available()

    def get_option_chain(
        self,
        underlying: str,
        date: date
    ) -> pd.DataFrame:
        """
        獲取選擇權鏈（階段一實作）

        實作策略：
        1. 使用 Shioaji API 獲取選擇權合約列表
        2. 獲取每個合約的收盤快照
        3. 返回 DataFrame

        注意：階段一僅獲取收盤數據，不包含 bid/ask
        """
        if not self.is_available():
            logger.error(
                "[OPTION] ❌ Shioaji client not available. "
                "Please check API credentials and connection."
            )
            return pd.DataFrame()

        try:
            logger.info(
                f"[OPTION] 📥 Fetching option chain: {underlying} | Date: {date}"
            )

            # 步驟 1：獲取選擇權合約列表
            try:
                contracts = self._get_option_contracts(underlying)
            except Exception as e:
                logger.error(
                    f"[OPTION] ❌ Failed to get contract list for {underlying}: "
                    f"{type(e).__name__}: {str(e)}",
                    exc_info=True
                )
                return pd.DataFrame()

            if not contracts:
                logger.warning(
                    f"[OPTION] ⚠️  No option contracts found for {underlying}. "
                    f"This underlying may not have options available."
                )
                return pd.DataFrame()

            logger.debug(f"[OPTION] Found {len(contracts)} option contracts")

            # 步驟 2：獲取每個合約的快照數據
            data = []
            failed_count = 0

            for i, contract in enumerate(contracts):
                try:
                    snapshot = self._get_contract_snapshot(contract, date)
                    if snapshot:
                        data.append(snapshot)
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    if failed_count <= 5:  # 只記錄前 5 個錯誤
                        logger.warning(
                            f"[OPTION] Failed to get snapshot for {contract.code}: "
                            f"{type(e).__name__}: {str(e)}"
                        )

                # 每 100 個合約記錄進度
                if (i + 1) % 100 == 0:
                    logger.debug(
                        f"[OPTION] Progress: {i + 1}/{len(contracts)} contracts processed, "
                        f"{len(data)} successful, {failed_count} failed"
                    )

            if failed_count > 0:
                logger.warning(
                    f"[OPTION] ⚠️  {failed_count}/{len(contracts)} contracts failed to fetch snapshots. "
                    f"Success rate: {len(data)/len(contracts)*100:.1f}%"
                )

            if not data:
                logger.warning(
                    f"[OPTION] ⚠️  No option data retrieved for {underlying}. "
                    f"All {len(contracts)} contracts failed. This may indicate: "
                    f"1) Non-trading hours, 2) API rate limiting, 3) Data unavailable."
                )
                return pd.DataFrame()

            # 步驟 3：轉換為 DataFrame
            df = pd.DataFrame(data)
            logger.info(
                f"[OPTION] ✅ Retrieved {len(df)} option contracts for {underlying} "
                f"({len(df)/len(contracts)*100:.1f}% success rate)"
            )

            # 數據品質檢查
            if 'close' in df.columns:
                valid_prices = df['close'].notna().sum()
                logger.debug(
                    f"[OPTION] Data quality: {valid_prices}/{len(df)} contracts have valid prices"
                )

            return df

        except Exception as e:
            logger.error(
                f"[OPTION] ❌ Unexpected error fetching option chain for {underlying}: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return pd.DataFrame()

    def get_minute_kbars(
        self,
        contract_id: str,
        start: date,
        end: date
    ) -> pd.DataFrame:
        """
        獲取選擇權分鐘線（階段二實作）

        注意：階段一暫不實作，返回空 DataFrame
        """
        logger.warning(
            f"[OPTION] Minute kbars not implemented in Stage 1. "
            f"Contract: {contract_id}, Start: {start}, End: {end}"
        )
        return pd.DataFrame()

    def _get_option_contracts(self, underlying: str) -> List:
        """
        獲取選擇權合約列表

        Args:
            underlying: 標的代碼（如 'TX', 'MTX'）

        Returns:
            List of contract objects
        """
        if not self._api:
            return []

        try:
            # Shioaji 選擇權合約位置：
            # - 台指選擇權：self._api.Contracts.Options.TXO
            # - 小台選擇權：self._api.Contracts.Options.MXO（如果有）

            if underlying in ['TX', 'TXCONT']:
                # 台指選擇權
                option_contracts_obj = self._api.Contracts.Options.TXO

                # 轉換為列表（Shioaji 合約對象需要特殊處理）
                contracts_list = []
                try:
                    # 方法 1：檢查是否有 __iter__ 方法
                    if hasattr(option_contracts_obj, '__iter__'):
                        contracts_list = list(option_contracts_obj)
                    # 方法 2：檢查是否是字典結構
                    elif hasattr(option_contracts_obj, 'values'):
                        contracts_list = list(option_contracts_obj.values())
                    # 方法 3：檢查是否有 items 方法
                    elif hasattr(option_contracts_obj, 'items'):
                        contracts_list = [contract for _, contract in option_contracts_obj.items()]
                    else:
                        logger.warning(f"[OPTION] Unknown TXO contract structure: {type(option_contracts_obj)}")
                        return []

                    logger.debug(f"[OPTION] Found {len(contracts_list)} TXO contracts")
                    return contracts_list

                except Exception as e:
                    logger.error(f"[OPTION] Failed to convert TXO contracts to list: {str(e)}")
                    return []

            elif underlying in ['MTX', 'MTXCONT']:
                # 小台選擇權（檢查是否存在）
                if hasattr(self._api.Contracts.Options, 'MXO'):
                    option_contracts_obj = self._api.Contracts.Options.MXO

                    # 同樣的轉換邏輯
                    contracts_list = []
                    try:
                        if hasattr(option_contracts_obj, '__iter__'):
                            contracts_list = list(option_contracts_obj)
                        elif hasattr(option_contracts_obj, 'values'):
                            contracts_list = list(option_contracts_obj.values())
                        elif hasattr(option_contracts_obj, 'items'):
                            contracts_list = [contract for _, contract in option_contracts_obj.items()]
                        else:
                            logger.warning(f"[OPTION] Unknown MXO contract structure: {type(option_contracts_obj)}")
                            return []

                        logger.debug(f"[OPTION] Found {len(contracts_list)} MXO contracts")
                        return contracts_list

                    except Exception as e:
                        logger.error(f"[OPTION] Failed to convert MXO contracts to list: {str(e)}")
                        return []
                else:
                    logger.warning("[OPTION] MXO contracts not available")
                    return []

            else:
                # 個股選擇權（階段一不支援）
                logger.warning(f"[OPTION] Stock options not supported in Stage 1: {underlying}")
                return []

        except Exception as e:
            logger.error(f"[OPTION] Error getting option contracts: {str(e)}")
            return []

    def _get_contract_snapshot(self, contract, date: date) -> Optional[Dict[str, Any]]:
        """
        獲取單一合約的快照數據

        Args:
            contract: Shioaji contract object
            date: 資料日期

        Returns:
            字典包含合約資訊和價格數據，失敗返回 None
        """
        try:
            # 解析合約資訊
            contract_info = self._parse_contract(contract)

            if not contract_info:
                return None

            # 階段一：使用 snapshots API 獲取收盤數據
            # 注意：Shioaji API 可能需要調整，這裡提供參考實作
            snapshot = self._api.snapshots([contract])

            if not snapshot or len(snapshot) == 0:
                logger.debug(f"[OPTION] No snapshot data for {contract.code}")
                return None

            snap_data = snapshot[0]

            # 提取價格和成交量數據
            data = {
                **contract_info,
                'close': float(snap_data.close) if hasattr(snap_data, 'close') else None,
                'volume': int(snap_data.volume) if hasattr(snap_data, 'volume') else 0,
                'open_interest': int(snap_data.open_interest) if hasattr(snap_data, 'open_interest') else None,
            }

            return data

        except Exception as e:
            logger.debug(f"[OPTION] Error getting snapshot for {contract.code}: {str(e)}")
            return None

    def _parse_contract(self, contract) -> Optional[Dict[str, Any]]:
        """
        解析 Shioaji 合約物件

        Args:
            contract: Shioaji contract object

        Returns:
            字典包含合約基本資訊
        """
        try:
            # Shioaji 選擇權合約屬性參考：
            # - code: 合約代碼（如 TXO202512C23000）
            # - symbol: 標的代碼
            # - strike_price: 履約價
            # - option_right: OptionRight.Call / OptionRight.Put
            # - delivery_date: 到期日

            contract_id = contract.code

            # 解析選擇權類型
            if hasattr(contract, 'option_right'):
                option_type = 'CALL' if 'Call' in str(contract.option_right) else 'PUT'
            else:
                # 從合約代碼推斷（備用方法）
                option_type = 'CALL' if 'C' in contract_id else 'PUT'

            # 解析標的代碼
            if contract_id.startswith('TXO'):
                underlying_id = 'TX'
                underlying_type = 'FUTURES'
            elif contract_id.startswith('MXO'):
                underlying_id = 'MTX'
                underlying_type = 'FUTURES'
            else:
                # 個股選擇權（階段一不支援）
                logger.debug(f"[OPTION] Unsupported option type: {contract_id}")
                return None

            return {
                'contract_id': contract_id,
                'underlying_id': underlying_id,
                'underlying_type': underlying_type,
                'option_type': option_type,
                'strike_price': float(contract.strike_price),
                'expiry_date': contract.delivery_date if hasattr(contract, 'delivery_date') else None,
            }

        except Exception as e:
            logger.error(f"[OPTION] Error parsing contract: {str(e)}")
            return None


class QlibOptionDataSource(OptionDataSource):
    """
    Qlib 選擇權資料源（未來擴展）

    用途：從 Qlib 二進制文件讀取選擇權數據（用於離線回測）
    階段：二或三
    """

    def __init__(self, qlib_dir: str):
        self.qlib_dir = qlib_dir

    def get_option_chain(self, underlying: str, date: date) -> pd.DataFrame:
        """從 Qlib 讀取選擇權鏈（階段二實作）"""
        logger.warning("[OPTION] Qlib data source not implemented yet")
        return pd.DataFrame()

    def get_minute_kbars(self, contract_id: str, start: date, end: date) -> pd.DataFrame:
        """從 Qlib 讀取分鐘線（階段二實作）"""
        logger.warning("[OPTION] Qlib data source not implemented yet")
        return pd.DataFrame()

    def is_available(self) -> bool:
        """檢查 Qlib 資料源是否可用"""
        return False  # 階段一不實作
