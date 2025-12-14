"""
Shioaji API Client

永豐證券 Shioaji API 客戶端，提供分鐘級股票數據獲取功能。
參考 FinLabClient 架構模式實作。
"""
import shioaji as sj
from typing import Optional, List
from datetime import datetime, timedelta, date
import calendar
import pandas as pd
from loguru import logger
from app.core.config import settings
from app.core.trading_hours import filter_trading_hours


def get_third_wednesday(year: int, month: int) -> date:
    """
    計算指定年月的第三個周三（台股期貨結算日）

    Args:
        year: 年份
        month: 月份

    Returns:
        第三個周三的日期
    """
    # 獲取該月第一天是星期幾（0=Monday, 6=Sunday）
    first_day = date(year, month, 1)
    first_weekday = first_day.weekday()  # 0=Monday, 2=Wednesday

    # 計算第一個周三是幾號
    # 如果第一天是周三（weekday=2），則第一個周三就是 1 號
    # 如果第一天是周四（weekday=3），則第一個周三是上週，下一個周三是 1 + (7 - 1) = 7 號
    # 如果第一天是周二（weekday=1），則第一個周三是 1 + (2 - 1) = 2 號
    if first_weekday <= 2:  # Monday=0, Tuesday=1, Wednesday=2
        first_wednesday_day = 1 + (2 - first_weekday)
    else:  # Thursday=3, Friday=4, Saturday=5, Sunday=6
        first_wednesday_day = 1 + (7 - first_weekday + 2)

    # 第三個周三 = 第一個周三 + 14 天
    third_wednesday_day = first_wednesday_day + 14

    return date(year, month, third_wednesday_day)


def is_contract_expired(contract_month_str: str, current_date: Optional[date] = None) -> bool:
    """
    判斷期貨合約是否已到期

    Args:
        contract_month_str: 合約月份字串（格式：YYYYMM，例如 '202512'）
        current_date: 當前日期（None 則使用今天）

    Returns:
        True 表示已到期，False 表示未到期
    """
    if current_date is None:
        current_date = date.today()

    try:
        year = int(contract_month_str[:4])
        month = int(contract_month_str[4:6])

        # 計算該合約的結算日（第三個周三）
        settlement_date = get_third_wednesday(year, month)

        # 如果當前日期 > 結算日，則已到期
        return current_date > settlement_date
    except (ValueError, IndexError):
        logger.warning(f"Invalid contract month format: {contract_month_str}")
        return False


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

    def _is_futures(self, symbol: str) -> bool:
        """
        判斷標的是否為期貨

        Args:
            symbol: 標的代碼

        Returns:
            bool: True 表示期貨，False 表示股票
        """
        return symbol in ['TX', 'MTX']

    def get_contract(self, stock_id: str, contract_type: str = 'stock'):
        """
        獲取契約（支持股票和期貨）

        Args:
            stock_id: 標的代碼（如 '2330' 或 'TX'）
            contract_type: 契約類型（'stock' 或 'futures'）

        Returns:
            Contract 物件，失敗返回 None
        """
        if not self.is_available():
            raise RuntimeError("Shioaji client not initialized")

        try:
            # 自動判斷契約類型
            if contract_type == 'stock' or contract_type == 'auto':
                if self._is_futures(stock_id):
                    # 自動識別為期貨（返回 contract 對象，忽略 contract_id）
                    result = self._get_futures_contract(stock_id)
                    if result:
                        return result[0]  # 只返回 contract 對象
                    return None
                else:
                    # 股票契約
                    contract = self._api.Contracts.Stocks[stock_id]
                    logger.debug(f"Found stock contract for {stock_id}: {contract}")
                    return contract

            elif contract_type == 'futures':
                # 期貨契約（返回 contract 對象，忽略 contract_id）
                result = self._get_futures_contract(stock_id)
                if result:
                    return result[0]  # 只返回 contract 對象
                return None

            else:
                logger.error(f"Unknown contract_type: {contract_type}")
                return None

        except KeyError:
            logger.error(f"Contract {stock_id} not found in Shioaji")
            return None
        except Exception as e:
            logger.error(f"Error getting contract for {stock_id}: {str(e)}")
            return None

    def get_futures_contract_id(self, symbol: str, current_date: Optional[date] = None) -> Optional[str]:
        """
        獲取期貨的實際合約代碼（用於存儲月份合約數據）

        Args:
            symbol: 期貨代碼（'TX' 或 'MTX'）
            current_date: 當前日期（None 則使用今天）

        Returns:
            實際合約代碼（如 "TX202512"），失敗返回 None
        """
        result = self._get_futures_contract(symbol, current_date)
        if result:
            return result[1]  # 返回 contract_id
        return None

    def _select_futures_contract_by_type(
        self,
        symbol: str,
        contracts_obj,
        prefix: str,
        current_date: date
    ):
        """
        通用的期貨合約選擇邏輯（消除 TX 和 MTX 重複代碼）

        Args:
            symbol: 期貨代碼（'TX' 或 'MTX'）
            contracts_obj: Shioaji 合約對象（如 self._api.Contracts.Futures.TXF）
            prefix: 合約前綴（'TXF' 或 'MXF'）
            current_date: 當前日期

        Returns:
            (contract, actual_contract_id): 期貨契約物件和實際合約代碼
            失敗時返回 None
        """
        logger.info(f"[FUTURES] Available {symbol} contracts: {contracts_obj}")

        # 獲取所有合約屬性（格式：TXF202512, MXF202601 等）
        contract_attrs = [
            attr for attr in dir(contracts_obj)
            if attr.startswith(prefix) and not attr.startswith(f'{prefix}_')
        ]

        if not contract_attrs:
            logger.error(f"[FUTURES] No {symbol} futures contracts found")
            return None

        # 排序合約（按月份排序）
        contract_attrs.sort()

        # 過濾掉已到期的合約
        valid_contracts = []
        for contract_name in contract_attrs:
            # 提取月份部分（例如 TXF202512 -> 202512）
            month_str = contract_name[len(prefix):]
            if not is_contract_expired(month_str, current_date):
                valid_contracts.append(contract_name)
            else:
                logger.debug(f"[FUTURES] Skipping expired contract: {contract_name}")

        if not valid_contracts:
            logger.error(f"[FUTURES] No valid (non-expired) {symbol} contracts found")
            return None

        # 選擇未到期合約中最近月份的主力合約
        selected_contract_name = valid_contracts[0]
        contract = getattr(contracts_obj, selected_contract_name)

        # 計算該合約的結算日
        month_str = selected_contract_name[len(prefix):]
        year = int(month_str[:4])
        month = int(month_str[4:6])
        settlement_date = get_third_wednesday(year, month)

        # 構造實際合約代碼（TX202512 或 MTX202512）
        actual_contract_id = f"{symbol}{month_str}"

        logger.info(
            f"[FUTURES] Selected {symbol} contract: {selected_contract_name} → {actual_contract_id} "
            f"(settlement: {settlement_date}, {contract})"
        )
        return contract, actual_contract_id

    def _get_futures_contract(self, symbol: str, current_date: Optional[date] = None):
        """
        獲取期貨契約（自动选择主力合约，支持自动换月）

        自動換月邏輯：
        - 台股期貨每月第三個周三到期
        - 過濾掉已到期的合約
        - 選擇未到期合約中最近月份的主力合約

        Args:
            symbol: 期貨代碼（'TX' 或 'MTX'）
            current_date: 當前日期（None 則使用今天，主要用於測試）

        Returns:
            (contract, actual_contract_id): 期貨契約物件和實際合約代碼（如 "TX202512"）
        """
        # 期貨配置映射表（易於擴展）
        FUTURES_CONFIG = {
            'TX': {
                'contracts_obj': self._api.Contracts.Futures.TXF,
                'prefix': 'TXF',
                'name': '台指期貨'
            },
            'MTX': {
                'contracts_obj': self._api.Contracts.Futures.MXF,
                'prefix': 'MXF',
                'name': '小台指期貨'
            }
        }

        # 輸入驗證
        if symbol not in FUTURES_CONFIG:
            logger.error(f"Unknown futures symbol: {symbol}. Supported symbols: {list(FUTURES_CONFIG.keys())}")
            return None

        if current_date is None:
            current_date = date.today()

        try:
            config = FUTURES_CONFIG[symbol]
            return self._select_futures_contract_by_type(
                symbol=symbol,
                contracts_obj=config['contracts_obj'],
                prefix=config['prefix'],
                current_date=current_date
            )

        except AttributeError as e:
            logger.error(f"Futures contracts not available in Shioaji API: {e}")
            logger.error("Please check your Shioaji API version and permissions")
            return None
        except Exception as e:
            logger.error(f"Error getting futures contract for {symbol}: {str(e)}")
            return None

    def get_kbars(
        self,
        stock_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        timeframe: str = '1min',
        contract_type: str = 'auto'
    ) -> Optional[pd.DataFrame]:
        """
        獲取 K 線數據（支持股票和期貨）

        Args:
            stock_id: 標的代碼（如 '2330' 或 'TX'）
            start_datetime: 開始時間（包含時分秒）
            end_datetime: 結束時間（包含時分秒）
            timeframe: 時間粒度（'1min', '5min', '15min', '30min', '60min', '1day'）
            contract_type: 契約類型（'auto', 'stock', 'futures'）

        Returns:
            DataFrame: columns=[datetime, open, high, low, close, volume]
            失敗返回 None

        注意事項：
            - Shioaji 歷史資料通常限制 3-6 個月
            - 股票：只返回交易時段數據（09:00-13:30）
            - 期貨：返回日盤 + 夜盤數據（08:45-13:45, 15:00-次日05:00）
            - 成交量單位為股數/口數
        """
        if not self.is_available():
            logger.error("Shioaji client not available")
            return None

        # 判斷是否為期貨
        is_futures = self._is_futures(stock_id) or contract_type == 'futures'

        # 獲取契約
        contract = self.get_contract(stock_id, contract_type=contract_type)
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

            # 期貨：不過濾交易時段（包含夜盤）
            # 股票：過濾交易時段（日盤 09:00-13:30）
            if not is_futures:
                df = filter_trading_hours(df, datetime_column='datetime', include_night=False)
            else:
                logger.info(f"Futures {stock_id}: keeping all trading hours (including night session)")

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
