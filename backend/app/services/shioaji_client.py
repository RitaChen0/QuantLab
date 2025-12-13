"""
Shioaji API Client

永豐證券 Shioaji API 客戶端，提供分鐘級股票數據獲取功能。
參考 FinLabClient 架構模式實作。
"""
import shioaji as sj
from typing import Optional, List
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from app.core.config import settings
from app.core.trading_hours import filter_trading_hours


class ShioajiClient:
    """
    永豐證券 Shioaji API 客戶端

    功能：
    - 獲取歷史分鐘 K 線數據
    - 獲取即時報價（選用）
    - 自動登入/登出管理（Context Manager）

    使用範例：
        with ShioajiClient() as client:
            if client.is_available():
                df = client.get_kbars('2330', start, end, '1min')
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        person_id: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        初始化 Shioaji 客戶端

        Args:
            api_key: API Key（從環境變數取得，選填）
            secret_key: Secret Key（從環境變數取得，選填）
            person_id: 證券帳號（用於激活憑證，選填）
            password: 憑證密碼（用於激活憑證，選填）
        """
        # 使用環境變數或參數
        self.api_key = api_key or settings.SHIOAJI_API_KEY
        self.secret_key = secret_key or settings.SHIOAJI_SECRET_KEY
        self.person_id = person_id or getattr(settings, 'SHIOAJI_PERSON_ID', None)
        self.password = password or getattr(settings, 'SHIOAJI_PASSWORD', None)

        self._api: Optional[sj.Shioaji] = None
        self._initialized = False

        # 如果有 API Key，自動初始化
        if self.api_key and self.secret_key:
            self._initialize()
        else:
            logger.warning("Shioaji API Key not configured. Client will not be available.")

    def _initialize(self):
        """初始化 Shioaji API 連接"""
        try:
            logger.info("Initializing Shioaji client...")
            self._api = sj.Shioaji()

            # 登入
            self._api.login(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            logger.info("✅ Shioaji client logged in successfully")
            self._initialized = True

            # 可選：激活憑證（用於下單功能）
            if self.person_id and self.password:
                try:
                    self._api.activate_ca(
                        ca_passwd=self.password,
                        person_id=self.person_id
                    )
                    logger.info("✅ Shioaji CA activated (trading enabled)")
                except Exception as e:
                    logger.warning(f"⚠️  CA activation failed (data-only mode): {str(e)}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Shioaji: {str(e)}")
            self._initialized = False

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用

        Returns:
            bool: 可用返回 True，否則返回 False
        """
        return self._initialized and self._api is not None

    def __enter__(self):
        """Context manager 進入"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager 退出：自動登出

        確保資源正確釋放，避免連線洩漏。
        """
        if self._api:
            try:
                self._api.logout()
                logger.info("Shioaji client logged out")
            except Exception as e:
                logger.error(f"Failed to logout: {str(e)}")

    def get_contract(self, stock_id: str):
        """
        獲取股票契約

        Args:
            stock_id: 股票代碼（如 '2330'）

        Returns:
            Contract 物件，失敗返回 None
        """
        if not self.is_available():
            raise RuntimeError("Shioaji client not initialized")

        try:
            # 自動判斷 TSE（上市）或 OTC（上櫃）
            # Shioaji 會自動搜尋所有市場
            contract = self._api.Contracts.Stocks[stock_id]
            logger.debug(f"Found contract for {stock_id}: {contract}")
            return contract
        except KeyError:
            logger.error(f"Stock {stock_id} not found in Shioaji contracts")
            return None
        except Exception as e:
            logger.error(f"Error getting contract for {stock_id}: {str(e)}")
            return None

    def get_kbars(
        self,
        stock_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        timeframe: str = '1min'
    ) -> Optional[pd.DataFrame]:
        """
        獲取 K 線數據

        Args:
            stock_id: 股票代碼（如 '2330'）
            start_datetime: 開始時間（包含時分秒）
            end_datetime: 結束時間（包含時分秒）
            timeframe: 時間粒度（'1min', '5min', '15min', '30min', '60min', '1day'）

        Returns:
            DataFrame: columns=[datetime, open, high, low, close, volume]
            失敗返回 None

        注意事項：
            - Shioaji 歷史資料通常限制 3-6 個月
            - 只返回交易時段數據（09:00-13:30）
            - 成交量單位為股數
        """
        if not self.is_available():
            logger.error("Shioaji client not available")
            return None

        # 獲取契約
        contract = self.get_contract(stock_id)
        if not contract:
            return None

        # 注意：新版 Shioaji API (v1.2.9+) 的 kbars 方法只返回 1 分鐘數據
        # 不再支援 kbar_type 參數
        try:
            logger.info(f"Fetching {timeframe} kbars for {stock_id} "
                       f"from {start_datetime} to {end_datetime}")

            # 調用 Shioaji API（新版僅支援 1min，其他粒度需後處理）
            kbars = self._api.kbars(
                contract=contract,
                start=start_datetime.strftime('%Y-%m-%d'),
                end=end_datetime.strftime('%Y-%m-%d'),
                timeout=30000
            )

            if not kbars or len(kbars.ts) == 0:
                logger.warning(f"No kbars data returned for {stock_id}")
                return None

            # 轉換為 DataFrame（新版 Shioaji API 返回 Kbars 物件，有 ts/Open/High/Low/Close/Volume 列表）
            data = []
            for i in range(len(kbars.ts)):
                # ts 是 nano秒時間戳，需要轉換為 datetime
                timestamp_ns = kbars.ts[i]
                dt = pd.to_datetime(timestamp_ns, unit='ns')

                data.append({
                    'datetime': dt,
                    'open': float(kbars.Open[i]),
                    'high': float(kbars.High[i]),
                    'low': float(kbars.Low[i]),
                    'close': float(kbars.Close[i]),
                    'volume': int(kbars.Volume[i])
                })

            df = pd.DataFrame(data)

            if df.empty:
                logger.warning(f"Empty DataFrame for {stock_id}")
                return None

            # 確保 datetime 為 datetime 類型
            df['datetime'] = pd.to_datetime(df['datetime'])

            # 使用配置化交易時段過濾（日盤 09:00-13:30）
            # 如需支持夜盘（期货），可传入 include_night=True
            df = filter_trading_hours(df, datetime_column='datetime', include_night=False)

            logger.info(f"✅ Fetched {len(df)} kbars for {stock_id} ({timeframe})")
            return df

        except Exception as e:
            logger.error(f"❌ Failed to fetch kbars for {stock_id}: {str(e)}")
            return None

    def get_quote(self, stock_id: str) -> Optional[dict]:
        """
        獲取即時報價（選用功能）

        Args:
            stock_id: 股票代碼（如 '2330'）

        Returns:
            dict: {
                'stock_id': str,
                'price': float,
                'volume': int,
                'timestamp': datetime
            }
            失敗返回 None
        """
        if not self.is_available():
            logger.error("Shioaji client not available")
            return None

        contract = self.get_contract(stock_id)
        if not contract:
            return None

        try:
            # 獲取即時報價
            quote = self._api.quote(contract)

            if not quote:
                logger.warning(f"No quote data for {stock_id}")
                return None

            return {
                'stock_id': stock_id,
                'price': float(quote.close),
                'volume': int(quote.volume),
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Failed to fetch quote for {stock_id}: {str(e)}")
            return None

    def subscribe_quote(self, stock_ids: List[str], callback):
        """
        訂閱即時報價（WebSocket，選用功能）

        Args:
            stock_ids: 股票代碼列表
            callback: 回調函數，接收 quote 數據

        注意：此功能需要持續運行的事件循環
        """
        if not self.is_available():
            logger.error("Shioaji client not available")
            return

        try:
            # 獲取契約列表
            contracts = [self.get_contract(sid) for sid in stock_ids]
            contracts = [c for c in contracts if c is not None]

            if not contracts:
                logger.warning("No valid contracts for subscription")
                return

            # 定義報價回調
            @self._api.quote.on_quote
            def quote_callback(exchange, tick):
                callback({
                    'stock_id': tick.code,
                    'price': float(tick.close),
                    'volume': int(tick.volume),
                    'timestamp': datetime.now()
                })

            # 訂閱
            for contract in contracts:
                self._api.quote.subscribe(contract, quote_type='tick')

            logger.info(f"Subscribed to {len(contracts)} stocks")

        except Exception as e:
            logger.error(f"Failed to subscribe quotes: {str(e)}")


# 全局單例實例（選用，避免重複登入）
_shioaji_client_instance: Optional[ShioajiClient] = None


def get_shioaji_client() -> ShioajiClient:
    """
    獲取全局 Shioaji 客戶端實例（單例模式）

    Returns:
        ShioajiClient 實例

    注意：全局實例需手動登出（非 Context Manager）
    """
    global _shioaji_client_instance

    if _shioaji_client_instance is None:
        _shioaji_client_instance = ShioajiClient()

    return _shioaji_client_instance
