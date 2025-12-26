"""
为现有模型补充代码

此脚本为已生成但缺少代码的模型补充 PyTorch 代码和 Qlib 配置
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.base import Base  # 导入 Base 确保所有模型被注册
from app.models.rdagent import GeneratedModel
from app.utils.model_code_generator import ModelCodeGenerator
from loguru import logger


def backfill_model_code(dry_run: bool = False):
    """为现有模型补充代码

    Args:
        dry_run: 是否为演练模式（不写入数据库）
    """
    db: Session = SessionLocal()

    try:
        # 查找所有没有代码的模型
        models_without_code = db.query(GeneratedModel).filter(
            GeneratedModel.code == None
        ).all()

        logger.info(f"Found {len(models_without_code)} models without code")

        for i, model in enumerate(models_without_code, 1):
            logger.info(f"\n[{i}/{len(models_without_code)}] Processing model: {model.name} (ID: {model.id})")
            logger.info(f"  Model Type: {model.model_type}")
            logger.info(f"  Architecture: {model.architecture[:100] if model.architecture else 'None'}...")

            if not model.architecture:
                logger.warning(f"  ⚠️  Skipping: No architecture description")
                continue

            try:
                # 生成代码和配置
                logger.info(f"  Generating code...")
                code, qlib_config = ModelCodeGenerator.generate_pytorch_code(
                    model_name=model.name,
                    model_type=model.model_type,
                    architecture=model.architecture,
                    hyperparameters=model.hyperparameters or {},
                    formulation=model.formulation
                )

                logger.info(f"  ✅ Code generated: {len(code)} characters")
                logger.info(f"  ✅ Qlib config generated")

                if not dry_run:
                    # 更新数据库
                    model.code = code
                    model.qlib_config = qlib_config
                    db.commit()
                    logger.info(f"  ✅ Database updated for model {model.id}")
                else:
                    logger.info(f"  🔍 [DRY RUN] Would update model {model.id}")

            except Exception as e:
                logger.error(f"  ❌ Failed to generate code for model {model.id}: {e}")
                continue

        logger.info(f"\n✅ Backfill completed!")
        logger.info(f"   Total models processed: {len(models_without_code)}")

    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}")
        raise

    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='为现有模型补充代码')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='演练模式（不写入数据库）'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("🔧 Backfilling Model Code")
    logger.info("=" * 60)

    if args.dry_run:
        logger.warning("⚠️  DRY RUN MODE - No database changes will be made")

    backfill_model_code(dry_run=args.dry_run)
