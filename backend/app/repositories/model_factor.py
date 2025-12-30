"""ModelFactor Repository"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.rdagent import ModelFactor, GeneratedFactor


class ModelFactorRepository:
    """模型因子關聯 Repository"""

    @staticmethod
    def create(
        db: Session,
        model_id: int,
        factor_id: int,
        feature_index: Optional[int] = None
    ) -> ModelFactor:
        """創建模型因子關聯"""
        model_factor = ModelFactor(
            model_id=model_id,
            factor_id=factor_id,
            feature_index=feature_index
        )
        db.add(model_factor)
        db.commit()
        db.refresh(model_factor)
        return model_factor

    @staticmethod
    def get_by_model(db: Session, model_id: int) -> List[ModelFactor]:
        """獲取模型的所有關聯因子"""
        return db.query(ModelFactor)\
            .filter(ModelFactor.model_id == model_id)\
            .order_by(ModelFactor.feature_index)\
            .all()

    @staticmethod
    def get_factors_by_model(db: Session, model_id: int) -> List[GeneratedFactor]:
        """獲取模型關聯的因子對象列表"""
        model_factors = db.query(ModelFactor)\
            .filter(ModelFactor.model_id == model_id)\
            .order_by(ModelFactor.feature_index)\
            .all()

        factor_ids = [mf.factor_id for mf in model_factors]

        if not factor_ids:
            return []

        return db.query(GeneratedFactor)\
            .filter(GeneratedFactor.id.in_(factor_ids))\
            .all()

    @staticmethod
    def delete_by_model(db: Session, model_id: int) -> int:
        """刪除模型的所有因子關聯"""
        count = db.query(ModelFactor)\
            .filter(ModelFactor.model_id == model_id)\
            .delete()
        db.commit()
        return count

    @staticmethod
    def batch_create(
        db: Session,
        model_id: int,
        factor_ids: List[int]
    ) -> List[ModelFactor]:
        """批次創建模型因子關聯"""
        # 先刪除現有關聯
        ModelFactorRepository.delete_by_model(db, model_id)

        # 創建新關聯
        model_factors = []
        for idx, factor_id in enumerate(factor_ids):
            mf = ModelFactor(
                model_id=model_id,
                factor_id=factor_id,
                feature_index=idx
            )
            model_factors.append(mf)

        db.add_all(model_factors)
        db.commit()

        for mf in model_factors:
            db.refresh(mf)

        return model_factors
