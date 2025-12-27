"""
資料庫連接池配置（改進版）

修正問題：
1. 區分 Backend 和 Celery Worker 的連接池大小
2. 防止多個 Worker 容器超過 PostgreSQL 連接限制
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from loguru import logger
from app.core.config import settings
import multiprocessing
import os

# 檢測當前是 Backend 還是 Celery Worker
IS_CELERY_WORKER = os.getenv('CELERY_WORKER_MODE', 'false').lower() == 'true'

if IS_CELERY_WORKER:
    # Celery Worker 配置（保守）
    # 每個 Worker 容器只需要少量連接
    pool_size = 5  # 基礎連接
    max_overflow = 10  # 高峰時額外連接
    max_connections = 15  # 每個 Worker 容器最多 15 個連接

    logger.info(
        f"[CELERY WORKER] Database connection pool: "
        f"pool_size={pool_size}, max_overflow={max_overflow}, "
        f"max_total={max_connections}"
    )
else:
    # Backend (FastAPI) 配置
    cpu_count = multiprocessing.cpu_count()
    fastapi_workers = int(os.getenv('FASTAPI_WORKERS', str(cpu_count)))

    # Backend 需要較多連接（處理 HTTP 請求）
    pool_size = max(10, fastapi_workers * 2)
    max_overflow = pool_size * 2
    max_connections = pool_size + max_overflow

    logger.info(
        f"[BACKEND] Database connection pool: "
        f"pool_size={pool_size}, max_overflow={max_overflow}, "
        f"max_total={max_connections} "
        f"(FastAPI workers: {fastapi_workers})"
    )

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=30,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models flag
_models_imported = False


def ensure_models_imported():
    """Ensure all models are imported"""
    global _models_imported
    if not _models_imported:
        from app.db.base import import_models
        import_models()
        _models_imported = True


def get_db():
    ensure_models_imported()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction_scope(db: Session):
    """資料庫交易 context manager"""
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"資料庫交易失敗，已回滾：{str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"交易時發生未預期錯誤，已回滾：{str(e)}")
        raise


def get_db_with_rollback():
    """資料庫會話依賴（帶自動 rollback）"""
    ensure_models_imported()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"資料庫操作失敗，已回滾：{str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"處理請求時發生錯誤，已回滾資料庫交易：{str(e)}")
        raise
    finally:
        db.close()
