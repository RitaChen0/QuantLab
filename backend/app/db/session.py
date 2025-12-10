from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from loguru import logger
from app.core.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models flag to prevent multiple imports
_models_imported = False


def ensure_models_imported():
    """Ensure all models are imported (call this before using SessionLocal)"""
    global _models_imported
    if not _models_imported:
        from app.db.base import import_models
        import_models()
        _models_imported = True


# Dependency for FastAPI routes
def get_db():
    ensure_models_imported()  # Ensure models are loaded before using DB
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction_scope(db: Session):
    """
    資料庫交易 context manager（帶自動 commit/rollback）

    自動處理交易的 commit 和 rollback，確保資料一致性。

    用法：
        with transaction_scope(db):
            db.add(obj)
            # ... 更多資料庫操作 ...
            # commit 自動執行

        # 錯誤時自動 rollback

    Args:
        db: SQLAlchemy Session

    Yields:
        SQLAlchemy Session

    Raises:
        SQLAlchemyError: 資料庫錯誤（rollback 後重新拋出）
    """
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
    """
    資料庫會話依賴（帶自動 rollback）

    用於 FastAPI 路由，自動處理錯誤回滾。

    用法：
        @router.post("/")
        async def create(db: Session = Depends(get_db_with_rollback)):
            # ... 資料庫操作 ...
            # 成功時自動 commit
            # 錯誤時自動 rollback

    Yields:
        SQLAlchemy Session
    """
    ensure_models_imported()
    db = SessionLocal()
    try:
        yield db
        db.commit()  # 請求成功時自動 commit
    except SQLAlchemyError as e:
        db.rollback()  # 資料庫錯誤時自動 rollback
        logger.error(f"資料庫操作失敗，已回滾：{str(e)}")
        raise
    except Exception as e:
        db.rollback()  # 其他錯誤也回滾
        logger.error(f"處理請求時發生錯誤，已回滾資料庫交易：{str(e)}")
        raise
    finally:
        db.close()
