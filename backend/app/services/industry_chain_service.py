"""
Industry Chain Service

整合 FinMind API 與產業鏈資料管理
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from loguru import logger

from app.repositories.industry_chain import (
    IndustryChainRepository,
    CustomIndustryCategoryRepository
)
from app.services.finmind_client import FinMindClient
from app.utils.cache import cached


class IndustryChainService:
    """FinMind 產業鏈服務"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = IndustryChainRepository()
        self.finmind = FinMindClient()

    # ========== Data Synchronization ==========

    def sync_finmind_industry_chains(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        從 FinMind API 同步產業鏈數據到資料庫

        Args:
            force_refresh: 是否強制刷新（清除現有數據）

        Returns:
            同步結果統計
        """
        try:
            logger.info("Starting FinMind industry chain synchronization")

            # 獲取 FinMind 產業鏈數據
            try:
                df = self.finmind.get_industry_chain()
            except Exception as api_error:
                # FinMind API 呼叫失敗，返回詳細錯誤
                error_msg = str(api_error)
                logger.error(f"FinMind API call failed: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "chains_added": 0,
                    "stocks_added": 0
                }

            if df.empty:
                logger.warning("No industry chain data from FinMind")
                return {
                    "status": "warning",
                    "message": "FinMind API 返回空數據，可能該數據集不可用或需要 API Token",
                    "chains_added": 0,
                    "stocks_added": 0
                }

            # 按產業鏈分組
            chain_groups = df.groupby('industry_chain')

            chains_added = 0
            stocks_added = 0

            for chain_name, group in chain_groups:
                # 創建或更新產業鏈
                chain = self.repo.upsert_chain(self.db, chain_name=chain_name)
                chains_added += 1

                # 批量添加股票
                stock_ids = group['stock_id'].tolist()
                count = self.repo.bulk_add_stocks_to_chain(
                    self.db,
                    chain_name=chain_name,
                    stock_ids=stock_ids
                )
                stocks_added += count

            logger.info(
                f"FinMind sync completed: {chains_added} chains, "
                f"{stocks_added} new stock mappings"
            )

            return {
                "status": "success",
                "chains_added": chains_added,
                "stocks_added": stocks_added,
                "total_records": len(df)
            }

        except Exception as e:
            logger.error(f"Failed to sync FinMind industry chains: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Synchronization failed: {str(e)}"
            )

    # ========== Industry Chain CRUD ==========

    @cached(key_prefix="industry_chain:all", expiry=3600)  # 1 hour cache
    def get_all_chains(self) -> List[Dict[str, Any]]:
        """獲取所有產業鏈（含股票數量）"""
        chains = self.repo.get_all_chains(self.db)

        result = []
        for chain in chains:
            stock_count = len(self.repo.get_stocks_by_chain(
                self.db, chain.chain_name
            ))
            result.append({
                "id": chain.id,
                "chain_name": chain.chain_name,
                "description": chain.description,
                "stock_count": stock_count,
                "created_at": chain.created_at,
                "updated_at": chain.updated_at
            })

        return result

    def get_chain_by_name(self, chain_name: str) -> Optional[Dict[str, Any]]:
        """獲取單個產業鏈詳情"""
        chain = self.repo.get_chain_by_name(self.db, chain_name)
        if not chain:
            return None

        stocks = self.repo.get_stocks_by_chain(self.db, chain_name)

        return {
            "id": chain.id,
            "chain_name": chain.chain_name,
            "description": chain.description,
            "stock_count": len(stocks),
            "stocks": stocks,
            "created_at": chain.created_at,
            "updated_at": chain.updated_at
        }

    def search_chains(
        self,
        keyword: Optional[str] = None,
        stock_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜尋產業鏈"""
        if stock_id:
            # 根據股票代號搜尋
            chain_names = self.repo.get_chains_by_stock(self.db, stock_id)
            chains = []
            for chain_name in chain_names:
                chain = self.get_chain_by_name(chain_name)
                if chain:
                    chains.append(chain)
            return chains

        # 根據關鍵字搜尋
        all_chains = self.get_all_chains()

        if keyword:
            keyword_lower = keyword.lower()
            return [
                chain for chain in all_chains
                if keyword_lower in chain['chain_name'].lower() or
                   (chain.get('description') and keyword_lower in chain['description'].lower())
            ]

        return all_chains

    # ========== Stock Management ==========

    def get_stocks_by_chain(
        self,
        chain_name: str,
        primary_only: bool = False
    ) -> List[str]:
        """獲取產業鏈中的股票"""
        chain = self.repo.get_chain_by_name(self.db, chain_name)
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Industry chain '{chain_name}' not found"
            )

        return self.repo.get_stocks_by_chain(self.db, chain_name, primary_only)

    def add_stock_to_chain(
        self,
        stock_id: str,
        chain_name: str,
        is_primary: bool = False
    ) -> Dict[str, Any]:
        """將股票添加到產業鏈"""
        try:
            stock_chain = self.repo.add_stock_to_chain(
                self.db, stock_id, chain_name, is_primary
            )
            return {
                "id": stock_chain.id,
                "stock_id": stock_chain.stock_id,
                "chain_name": stock_chain.chain_name,
                "is_primary": stock_chain.is_primary
            }
        except Exception as e:
            logger.error(f"Failed to add stock to chain: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # ========== Statistics ==========

    @cached(key_prefix="industry_chain:statistics", expiry=1800)  # 30 minutes cache
    def get_statistics(self) -> Dict[str, Any]:
        """獲取產業鏈統計信息"""
        return self.repo.get_chain_statistics(self.db)

    # ========== FinMind API Direct Access ==========

    def get_finmind_chains(self) -> List[str]:
        """直接從 FinMind API 獲取產業鏈列表（不經過資料庫）"""
        return self.finmind.get_all_industry_chains()

    def get_finmind_stocks_by_chain(self, chain_name: str) -> List[str]:
        """直接從 FinMind API 獲取產業鏈股票（不經過資料庫）"""
        return self.finmind.get_stocks_by_industry_chain(chain_name)


class CustomIndustryCategoryService:
    """自定義產業分類服務"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = CustomIndustryCategoryRepository()

    # ========== Category CRUD ==========

    def get_user_categories(
        self,
        user_id: int,
        parent_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """獲取用戶的所有分類"""
        categories = self.repo.get_user_categories(self.db, user_id, parent_id)

        result = []
        for category in categories:
            stock_count = len(self.repo.get_stocks_in_category(
                self.db, category.id
            ))
            result.append({
                "id": category.id,
                "category_name": category.category_name,
                "description": category.description,
                "parent_id": category.parent_id,
                "stock_count": stock_count,
                "created_at": category.created_at,
                "updated_at": category.updated_at
            })

        return result

    def get_category_by_id(
        self,
        category_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """獲取單個分類詳情"""
        category = self.repo.get_category_by_id(self.db, category_id, user_id)
        if not category:
            return None

        stocks = self.repo.get_stocks_in_category(self.db, category_id)

        return {
            "id": category.id,
            "category_name": category.category_name,
            "description": category.description,
            "parent_id": category.parent_id,
            "user_id": category.user_id,
            "stock_count": len(stocks),
            "stocks": stocks,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        }

    def create_category(
        self,
        user_id: int,
        category_name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """創建新分類"""
        try:
            category = self.repo.create_category(
                self.db, user_id, category_name, description, parent_id
            )
            return {
                "id": category.id,
                "category_name": category.category_name,
                "description": category.description,
                "parent_id": category.parent_id,
                "user_id": category.user_id,
                "created_at": category.created_at,
                "updated_at": category.updated_at
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def update_category(
        self,
        category_id: int,
        user_id: int,
        category_name: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """更新分類"""
        try:
            category = self.repo.update_category(
                self.db, category_id, user_id,
                category_name, description, parent_id
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )
            return self.get_category_by_id(category_id, user_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def delete_category(
        self,
        category_id: int,
        user_id: int,
        cascade: bool = False
    ) -> bool:
        """刪除分類"""
        try:
            return self.repo.delete_category(self.db, category_id, user_id, cascade)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # ========== Stock Management ==========

    def get_stocks_in_category(self, category_id: int) -> List[str]:
        """獲取分類中的股票"""
        return self.repo.get_stocks_in_category(self.db, category_id)

    def add_stock_to_category(
        self,
        category_id: int,
        stock_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """將股票添加到分類"""
        try:
            stock_category = self.repo.add_stock_to_category(
                self.db, category_id, stock_id, user_id
            )
            return {
                "id": stock_category.id,
                "category_id": stock_category.category_id,
                "stock_id": stock_category.stock_id,
                "created_at": stock_category.created_at
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def bulk_add_stocks(
        self,
        category_id: int,
        stock_ids: List[str],
        user_id: int
    ) -> Dict[str, Any]:
        """批量添加股票到分類"""
        try:
            count = self.repo.bulk_add_stocks_to_category(
                self.db, category_id, stock_ids, user_id
            )
            return {
                "category_id": category_id,
                "stocks_added": count,
                "total_requested": len(stock_ids)
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def remove_stock_from_category(
        self,
        category_id: int,
        stock_id: str
    ) -> bool:
        """從分類中移除股票"""
        return self.repo.remove_stock_from_category(
            self.db, category_id, stock_id
        )

    # ========== Category Tree ==========

    @cached(key_prefix="custom_category:tree", expiry=600)  # 10 minutes cache
    def get_category_tree(self, user_id: int) -> List[Dict[str, Any]]:
        """獲取用戶的分類樹狀結構"""
        return self.repo.get_category_tree(self.db, user_id)

    # ========== Search ==========

    def search_categories(
        self,
        user_id: int,
        keyword: Optional[str] = None,
        stock_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜尋分類"""
        if stock_id:
            # 根據股票代號搜尋
            categories = self.repo.get_stock_categories(self.db, stock_id, user_id)
            return [
                self.get_category_by_id(cat.id, user_id)
                for cat in categories
            ]

        # 根據關鍵字搜尋
        all_categories = self.get_user_categories(user_id)

        if keyword:
            keyword_lower = keyword.lower()
            return [
                cat for cat in all_categories
                if keyword_lower in cat['category_name'].lower() or
                   (cat.get('description') and keyword_lower in cat['description'].lower())
            ]

        return all_categories
