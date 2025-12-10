"""
Qlib 量化投資平台配置

此模組負責初始化和配置 Qlib 環境。
"""
import os
from pathlib import Path
from loguru import logger


class QlibConfig:
    """Qlib 配置類"""

    def __init__(self):
        # 從環境變數讀取配置，提供預設值
        # 使用 /tmp 路徑避免權限問題
        self.data_path = os.getenv("QLIB_DATA_PATH", "/tmp/qlib_data")
        self.cache_path = os.getenv("QLIB_CACHE_PATH", "/tmp/qlib_cache")
        self.region = "cn"  # 使用中國市場配置（與台股類似）
        self.exp_manager = {
            "class": "MLflowExpManager",
            "module_path": "qlib.workflow.expm",
            "kwargs": {
                "uri": os.getenv("MLFLOW_URI", "file:///data/mlruns"),
                "default_exp_name": "QuantLab",
            },
        }

    def init_qlib(self, force: bool = False) -> bool:
        """
        初始化 Qlib 環境

        Args:
            force: 強制重新初始化（即使已初始化）

        Returns:
            bool: 初始化是否成功
        """
        try:
            import qlib
            from qlib.config import REG_CN

            # 檢查是否已初始化
            if hasattr(qlib, '_qlib_inited') and qlib._qlib_inited and not force:
                logger.info("Qlib already initialized, skipping...")
                return True

            # 確保快取目錄存在（數據目錄由 export 腳本創建）
            try:
                Path(self.cache_path).mkdir(parents=True, exist_ok=True)
            except PermissionError:
                logger.warning(f"Cannot create cache path {self.cache_path}, using /tmp")
                self.cache_path = "/tmp/qlib_cache"
                Path(self.cache_path).mkdir(parents=True, exist_ok=True)

            # 檢查數據目錄是否存在
            if not Path(self.data_path).exists():
                logger.warning(
                    f"Qlib data path {self.data_path} does not exist. "
                    f"Run export_to_qlib.py to create it."
                )
                # 創建空目錄避免錯誤
                try:
                    Path(self.data_path).mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    logger.error(f"Cannot create data path {self.data_path}")
                    return False

            # 初始化 Qlib（使用正確的配置格式）
            qlib.init(
                provider_uri=self.data_path,
                region=REG_CN,  # 使用中國市場配置
                expression_cache=None,  # 使用預設配置
                dataset_cache=None,  # 使用預設配置
                # auto_mount=True,  # 自動掛載數據
            )

            logger.info(
                f"✅ Qlib initialized successfully. Data path: {self.data_path}, "
                f"Cache path: {self.cache_path}"
            )
            return True

        except ImportError:
            logger.warning(
                "Qlib is not installed. Please install it: pip install pyqlib"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Qlib: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def is_qlib_available(self) -> bool:
        """
        檢查 Qlib 是否可用

        Returns:
            bool: Qlib 是否已安裝且可用
        """
        try:
            import qlib  # noqa: F401
            return True
        except ImportError:
            return False

    def get_data_path(self) -> str:
        """獲取 Qlib 數據路徑"""
        return self.data_path

    def get_cache_path(self) -> str:
        """獲取 Qlib 緩存路徑"""
        return self.cache_path


# 全局配置實例
qlib_config = QlibConfig()


def init_qlib_if_available():
    """
    如果 Qlib 可用，則初始化它
    此函數可在應用啟動時調用
    """
    if qlib_config.is_qlib_available():
        qlib_config.init_qlib()
    else:
        logger.info("Qlib is not available, skipping initialization")
