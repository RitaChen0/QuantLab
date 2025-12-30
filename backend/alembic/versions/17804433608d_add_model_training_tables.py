"""add_model_training_tables

Revision ID: 17804433608d
Revises: 13c246798d5c
Create Date: 2025-12-30 02:57:20.689163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17804433608d'
down_revision: Union[str, None] = '13c246798d5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 創建 model_factors 表（模型和因子關聯）
    op.create_table(
        'model_factors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('feature_index', sa.Integer(), nullable=True, comment='因子在特徵向量中的索引位置'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['factor_id'], ['generated_factors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['generated_models.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_factors_model_id', 'model_factors', ['model_id'])
    op.create_index('ix_model_factors_factor_id', 'model_factors', ['factor_id'])

    # 創建 model_training_jobs 表（訓練任務記錄）
    op.create_table(
        'model_training_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # 訓練配置
        sa.Column('dataset_config', sa.JSON(), nullable=True, comment='數據集配置（JSON）'),
        sa.Column('training_params', sa.JSON(), nullable=True, comment='訓練參數（JSON）'),

        # 訓練狀態
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING', comment='訓練狀態'),
        sa.Column('progress', sa.Float(), server_default='0.0', comment='訓練進度 0.0-1.0'),
        sa.Column('current_epoch', sa.Integer(), server_default='0', comment='當前訓練輪數'),
        sa.Column('total_epochs', sa.Integer(), nullable=True, comment='總訓練輪數'),
        sa.Column('current_step', sa.String(100), nullable=True, comment='當前步驟描述'),

        # 訓練指標
        sa.Column('train_loss', sa.Float(), nullable=True, comment='訓練損失'),
        sa.Column('valid_loss', sa.Float(), nullable=True, comment='驗證損失'),
        sa.Column('test_ic', sa.Float(), nullable=True, comment='測試集 IC'),
        sa.Column('test_metrics', sa.JSON(), nullable=True, comment='詳細測試指標（JSON）'),

        # 模型權重
        sa.Column('model_weight_path', sa.String(500), nullable=True, comment='訓練好的權重文件路徑'),

        # 訓練日誌
        sa.Column('training_log', sa.Text(), nullable=True, comment='訓練日誌（多行文本）'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='錯誤訊息'),

        # Celery 任務 ID
        sa.Column('celery_task_id', sa.String(255), nullable=True, comment='Celery 任務 ID'),

        # 時間戳
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='開始時間'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成時間'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.ForeignKeyConstraint(['model_id'], ['generated_models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_training_jobs_model_id', 'model_training_jobs', ['model_id'])
    op.create_index('ix_model_training_jobs_user_id', 'model_training_jobs', ['user_id'])
    op.create_index('ix_model_training_jobs_status', 'model_training_jobs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_model_training_jobs_status', table_name='model_training_jobs')
    op.drop_index('ix_model_training_jobs_user_id', table_name='model_training_jobs')
    op.drop_index('ix_model_training_jobs_model_id', table_name='model_training_jobs')
    op.drop_table('model_training_jobs')

    op.drop_index('ix_model_factors_factor_id', table_name='model_factors')
    op.drop_index('ix_model_factors_model_id', table_name='model_factors')
    op.drop_table('model_factors')
