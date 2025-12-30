"""ModelTrainingJob Repository"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.rdagent import ModelTrainingJob


class ModelTrainingJobRepository:
    """模型訓練任務 Repository"""

    @staticmethod
    def create(
        db: Session,
        model_id: int,
        user_id: int,
        dataset_config: Dict[str, Any],
        training_params: Dict[str, Any],
        celery_task_id: Optional[str] = None
    ) -> ModelTrainingJob:
        """創建訓練任務"""
        job = ModelTrainingJob(
            model_id=model_id,
            user_id=user_id,
            dataset_config=dataset_config,
            training_params=training_params,
            celery_task_id=celery_task_id,
            status="PENDING",
            progress=0.0,
            current_epoch=0,
            total_epochs=training_params.get('num_epochs', 100),
            training_log=""
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_by_id(db: Session, job_id: int) -> Optional[ModelTrainingJob]:
        """根據 ID 獲取訓練任務"""
        return db.query(ModelTrainingJob).filter(ModelTrainingJob.id == job_id).first()

    @staticmethod
    def get_by_user(
        db: Session,
        user_id: int,
        limit: int = 50
    ) -> List[ModelTrainingJob]:
        """獲取用戶的訓練任務列表"""
        return db.query(ModelTrainingJob)\
            .filter(ModelTrainingJob.user_id == user_id)\
            .order_by(desc(ModelTrainingJob.created_at))\
            .limit(limit)\
            .all()

    @staticmethod
    def get_by_model(
        db: Session,
        model_id: int,
        limit: int = 10
    ) -> List[ModelTrainingJob]:
        """獲取模型的訓練任務列表"""
        return db.query(ModelTrainingJob)\
            .filter(ModelTrainingJob.model_id == model_id)\
            .order_by(desc(ModelTrainingJob.created_at))\
            .limit(limit)\
            .all()

    @staticmethod
    def update_status(
        db: Session,
        job_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[ModelTrainingJob]:
        """更新任務狀態"""
        job = ModelTrainingJobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.status = status

        if status == "RUNNING" and not job.started_at:
            job.started_at = datetime.now(timezone.utc)

        if status in ["COMPLETED", "FAILED", "CANCELLED"]:
            job.completed_at = datetime.now(timezone.utc)
            if status == "COMPLETED":
                job.progress = 1.0

        if error_message:
            job.error_message = error_message

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def update_progress(
        db: Session,
        job_id: int,
        progress: float,
        current_epoch: int,
        current_step: Optional[str] = None,
        train_loss: Optional[float] = None,
        valid_loss: Optional[float] = None
    ) -> Optional[ModelTrainingJob]:
        """更新訓練進度"""
        job = ModelTrainingJobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.progress = progress
        job.current_epoch = current_epoch

        if current_step:
            job.current_step = current_step

        if train_loss is not None:
            job.train_loss = train_loss

        if valid_loss is not None:
            job.valid_loss = valid_loss

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def append_log(
        db: Session,
        job_id: int,
        log_message: str
    ) -> Optional[ModelTrainingJob]:
        """追加訓練日誌"""
        job = ModelTrainingJobRepository.get_by_id(db, job_id)
        if not job:
            return None

        # 追加日誌（每行一條訊息）
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        new_log = f"[{timestamp}] {log_message}\n"

        if job.training_log:
            job.training_log += new_log
        else:
            job.training_log = new_log

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def update_completed(
        db: Session,
        job_id: int,
        model_weight_path: str,
        test_ic: float,
        test_metrics: Dict[str, Any]
    ) -> Optional[ModelTrainingJob]:
        """更新訓練完成結果"""
        job = ModelTrainingJobRepository.get_by_id(db, job_id)
        if not job:
            return None

        job.status = "COMPLETED"
        job.progress = 1.0
        job.model_weight_path = model_weight_path
        job.test_ic = test_ic
        job.test_metrics = test_metrics
        job.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def delete(db: Session, job_id: int) -> bool:
        """刪除訓練任務"""
        job = ModelTrainingJobRepository.get_by_id(db, job_id)
        if not job:
            return False

        db.delete(job)
        db.commit()
        return True
