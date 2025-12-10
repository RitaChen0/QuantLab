"""
Industry Chain Repository

處理 FinMind 產業鏈和自定義產業分類的資料庫操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from app.models.industry_chain import (
    IndustryChain,
    StockIndustryChain,
    CustomIndustryCategory,
    StockCustomCategory
)


class IndustryChainRepository:
    """FinMind 產業鏈資料庫操作"""

    # ========== IndustryChain CRUD ==========

    def get_all_chains(self, db: Session) -> List[IndustryChain]:
        """獲取所有產業鏈"""
        return db.query(IndustryChain).order_by(IndustryChain.chain_name).all()

    def get_chain_by_name(self, db: Session, chain_name: str) -> Optional[IndustryChain]:
        """根據名稱獲取產業鏈"""
        return db.query(IndustryChain).filter(
            IndustryChain.chain_name == chain_name
        ).first()

    def create_chain(
        self,
        db: Session,
        chain_name: str,
        description: Optional[str] = None
    ) -> IndustryChain:
        """創建新產業鏈"""
        chain = IndustryChain(
            chain_name=chain_name,
            description=description
        )
        db.add(chain)
        db.commit()
        db.refresh(chain)
        return chain

    def upsert_chain(
        self,
        db: Session,
        chain_name: str,
        description: Optional[str] = None
    ) -> IndustryChain:
        """創建或更新產業鏈"""
        chain = self.get_chain_by_name(db, chain_name)
        if chain:
            if description:
                chain.description = description
                chain.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(chain)
        else:
            chain = self.create_chain(db, chain_name, description)
        return chain

    def delete_chain(self, db: Session, chain_name: str) -> bool:
        """刪除產業鏈（會級聯刪除關聯的股票）"""
        chain = self.get_chain_by_name(db, chain_name)
        if chain:
            db.delete(chain)
            db.commit()
            return True
        return False

    # ========== StockIndustryChain CRUD ==========

    def get_stocks_by_chain(
        self,
        db: Session,
        chain_name: str,
        primary_only: bool = False
    ) -> List[str]:
        """獲取產業鏈中的所有股票"""
        query = db.query(StockIndustryChain.stock_id).filter(
            StockIndustryChain.chain_name == chain_name
        )

        if primary_only:
            query = query.filter(StockIndustryChain.is_primary == True)

        return [row.stock_id for row in query.all()]

    def get_chains_by_stock(self, db: Session, stock_id: str) -> List[str]:
        """獲取股票所屬的所有產業鏈"""
        chains = db.query(StockIndustryChain.chain_name).filter(
            StockIndustryChain.stock_id == stock_id
        ).all()
        return [chain.chain_name for chain in chains]

    def get_primary_chain(self, db: Session, stock_id: str) -> Optional[str]:
        """獲取股票的主要產業鏈"""
        result = db.query(StockIndustryChain.chain_name).filter(
            StockIndustryChain.stock_id == stock_id,
            StockIndustryChain.is_primary == True
        ).first()
        return result.chain_name if result else None

    def add_stock_to_chain(
        self,
        db: Session,
        stock_id: str,
        chain_name: str,
        is_primary: bool = False
    ) -> StockIndustryChain:
        """將股票添加到產業鏈"""
        # 確保產業鏈存在
        chain = self.get_chain_by_name(db, chain_name)
        if not chain:
            chain = self.create_chain(db, chain_name)

        # 檢查是否已存在
        existing = db.query(StockIndustryChain).filter(
            StockIndustryChain.stock_id == stock_id,
            StockIndustryChain.chain_name == chain_name
        ).first()

        if existing:
            existing.is_primary = is_primary
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return existing

        # 創建新關聯
        stock_chain = StockIndustryChain(
            stock_id=stock_id,
            chain_name=chain_name,
            is_primary=is_primary
        )
        db.add(stock_chain)
        db.commit()
        db.refresh(stock_chain)
        return stock_chain

    def remove_stock_from_chain(
        self,
        db: Session,
        stock_id: str,
        chain_name: str
    ) -> bool:
        """從產業鏈中移除股票"""
        stock_chain = db.query(StockIndustryChain).filter(
            StockIndustryChain.stock_id == stock_id,
            StockIndustryChain.chain_name == chain_name
        ).first()

        if stock_chain:
            db.delete(stock_chain)
            db.commit()
            return True
        return False

    def bulk_add_stocks_to_chain(
        self,
        db: Session,
        chain_name: str,
        stock_ids: List[str],
        primary_stock_id: Optional[str] = None
    ) -> int:
        """批量添加股票到產業鏈"""
        # 確保產業鏈存在
        chain = self.get_chain_by_name(db, chain_name)
        if not chain:
            chain = self.create_chain(db, chain_name)

        # 獲取已存在的關聯
        existing = db.query(StockIndustryChain.stock_id).filter(
            StockIndustryChain.chain_name == chain_name,
            StockIndustryChain.stock_id.in_(stock_ids)
        ).all()
        existing_ids = {row.stock_id for row in existing}

        # 只添加新的關聯
        new_ids = set(stock_ids) - existing_ids
        count = 0

        for stock_id in new_ids:
            is_primary = (stock_id == primary_stock_id)
            stock_chain = StockIndustryChain(
                stock_id=stock_id,
                chain_name=chain_name,
                is_primary=is_primary
            )
            db.add(stock_chain)
            count += 1

        db.commit()
        return count

    # ========== Statistics ==========

    def get_chain_statistics(self, db: Session) -> Dict[str, Any]:
        """獲取產業鏈統計信息"""
        total_chains = db.query(func.count(IndustryChain.id)).scalar()
        total_mappings = db.query(func.count(StockIndustryChain.id)).scalar()

        # 每個產業鏈的股票數量
        chain_counts = db.query(
            StockIndustryChain.chain_name,
            func.count(StockIndustryChain.stock_id).label('stock_count')
        ).group_by(StockIndustryChain.chain_name).all()

        return {
            "total_chains": total_chains,
            "total_mappings": total_mappings,
            "chain_stock_counts": {
                row.chain_name: row.stock_count for row in chain_counts
            }
        }


class CustomIndustryCategoryRepository:
    """自定義產業分類資料庫操作"""

    # ========== CustomIndustryCategory CRUD ==========

    def get_user_categories(
        self,
        db: Session,
        user_id: int,
        parent_id: Optional[int] = None
    ) -> List[CustomIndustryCategory]:
        """獲取用戶的所有自定義分類"""
        query = db.query(CustomIndustryCategory).filter(
            CustomIndustryCategory.user_id == user_id
        )

        if parent_id is not None:
            query = query.filter(CustomIndustryCategory.parent_id == parent_id)

        return query.order_by(CustomIndustryCategory.category_name).all()

    def get_category_by_id(
        self,
        db: Session,
        category_id: int,
        user_id: Optional[int] = None
    ) -> Optional[CustomIndustryCategory]:
        """根據 ID 獲取分類"""
        query = db.query(CustomIndustryCategory).filter(
            CustomIndustryCategory.id == category_id
        )

        if user_id is not None:
            query = query.filter(CustomIndustryCategory.user_id == user_id)

        return query.first()

    def get_category_by_name(
        self,
        db: Session,
        user_id: int,
        category_name: str
    ) -> Optional[CustomIndustryCategory]:
        """根據名稱獲取分類"""
        return db.query(CustomIndustryCategory).filter(
            CustomIndustryCategory.user_id == user_id,
            CustomIndustryCategory.category_name == category_name
        ).first()

    def create_category(
        self,
        db: Session,
        user_id: int,
        category_name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> CustomIndustryCategory:
        """創建新分類"""
        # 檢查名稱是否已存在
        existing = self.get_category_by_name(db, user_id, category_name)
        if existing:
            raise ValueError(f"Category '{category_name}' already exists for this user")

        # 如果有父分類，驗證父分類是否屬於同一用戶
        if parent_id:
            parent = self.get_category_by_id(db, parent_id, user_id)
            if not parent:
                raise ValueError("Parent category not found or doesn't belong to user")

        category = CustomIndustryCategory(
            user_id=user_id,
            category_name=category_name,
            description=description,
            parent_id=parent_id
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    def update_category(
        self,
        db: Session,
        category_id: int,
        user_id: int,
        category_name: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> Optional[CustomIndustryCategory]:
        """更新分類"""
        category = self.get_category_by_id(db, category_id, user_id)
        if not category:
            return None

        if category_name:
            # 檢查新名稱是否與其他分類衝突
            existing = self.get_category_by_name(db, user_id, category_name)
            if existing and existing.id != category_id:
                raise ValueError(f"Category '{category_name}' already exists")
            category.category_name = category_name

        if description is not None:
            category.description = description

        if parent_id is not None:
            # 驗證父分類
            if parent_id != category_id:  # 防止自我引用
                parent = self.get_category_by_id(db, parent_id, user_id)
                if not parent:
                    raise ValueError("Parent category not found")
                category.parent_id = parent_id

        category.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(category)
        return category

    def delete_category(
        self,
        db: Session,
        category_id: int,
        user_id: int,
        cascade: bool = False
    ) -> bool:
        """刪除分類"""
        category = self.get_category_by_id(db, category_id, user_id)
        if not category:
            return False

        # 檢查是否有子分類
        children = self.get_user_categories(db, user_id, parent_id=category_id)
        if children and not cascade:
            raise ValueError("Category has child categories. Use cascade=True to delete all")

        # 遞迴刪除子分類
        if cascade:
            for child in children:
                self.delete_category(db, child.id, user_id, cascade=True)

        db.delete(category)
        db.commit()
        return True

    # ========== StockCustomCategory CRUD ==========

    def get_stocks_in_category(
        self,
        db: Session,
        category_id: int
    ) -> List[str]:
        """獲取分類中的所有股票"""
        stocks = db.query(StockCustomCategory.stock_id).filter(
            StockCustomCategory.category_id == category_id
        ).all()
        return [stock.stock_id for stock in stocks]

    def get_stock_categories(
        self,
        db: Session,
        stock_id: str,
        user_id: Optional[int] = None
    ) -> List[CustomIndustryCategory]:
        """獲取股票所屬的所有自定義分類"""
        query = db.query(CustomIndustryCategory).join(
            StockCustomCategory
        ).filter(
            StockCustomCategory.stock_id == stock_id
        )

        if user_id is not None:
            query = query.filter(CustomIndustryCategory.user_id == user_id)

        return query.all()

    def add_stock_to_category(
        self,
        db: Session,
        category_id: int,
        stock_id: str,
        user_id: Optional[int] = None
    ) -> StockCustomCategory:
        """將股票添加到自定義分類"""
        # 驗證分類存在且屬於用戶
        category = self.get_category_by_id(db, category_id, user_id)
        if not category:
            raise ValueError("Category not found")

        # 檢查是否已存在
        existing = db.query(StockCustomCategory).filter(
            StockCustomCategory.category_id == category_id,
            StockCustomCategory.stock_id == stock_id
        ).first()

        if existing:
            return existing

        # 創建新關聯
        stock_category = StockCustomCategory(
            category_id=category_id,
            stock_id=stock_id
        )
        db.add(stock_category)
        db.commit()
        db.refresh(stock_category)
        return stock_category

    def remove_stock_from_category(
        self,
        db: Session,
        category_id: int,
        stock_id: str
    ) -> bool:
        """從自定義分類中移除股票"""
        stock_category = db.query(StockCustomCategory).filter(
            StockCustomCategory.category_id == category_id,
            StockCustomCategory.stock_id == stock_id
        ).first()

        if stock_category:
            db.delete(stock_category)
            db.commit()
            return True
        return False

    def bulk_add_stocks_to_category(
        self,
        db: Session,
        category_id: int,
        stock_ids: List[str],
        user_id: Optional[int] = None
    ) -> int:
        """批量添加股票到自定義分類"""
        # 驗證分類
        category = self.get_category_by_id(db, category_id, user_id)
        if not category:
            raise ValueError("Category not found")

        # 獲取已存在的關聯
        existing = db.query(StockCustomCategory.stock_id).filter(
            StockCustomCategory.category_id == category_id,
            StockCustomCategory.stock_id.in_(stock_ids)
        ).all()
        existing_ids = {row.stock_id for row in existing}

        # 只添加新的關聯
        new_ids = set(stock_ids) - existing_ids
        count = 0

        for stock_id in new_ids:
            stock_category = StockCustomCategory(
                category_id=category_id,
                stock_id=stock_id
            )
            db.add(stock_category)
            count += 1

        db.commit()
        return count

    # ========== Category Tree ==========

    def get_category_tree(
        self,
        db: Session,
        user_id: int,
        parent_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """獲取分類樹狀結構"""
        categories = self.get_user_categories(db, user_id, parent_id)

        result = []
        for category in categories:
            # 獲取股票數量
            stock_count = db.query(func.count(StockCustomCategory.id)).filter(
                StockCustomCategory.category_id == category.id
            ).scalar()

            # 遞迴獲取子分類
            children = self.get_category_tree(db, user_id, category.id)

            result.append({
                "id": category.id,
                "name": category.category_name,
                "description": category.description,
                "parent_id": category.parent_id,
                "stock_count": stock_count,
                "children": children
            })

        return result
