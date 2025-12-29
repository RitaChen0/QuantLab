"""
因子評估 API 端點

提供因子績效評估相關的 API：
- 評估單個因子
- 獲取評估歷史
- 批量評估
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from loguru import logger

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.rdagent import GeneratedFactor, FactorEvaluation
from app.services.factor_evaluation_service import FactorEvaluationService
from app.core.rate_limit import limiter, RateLimits
from app.utils.logging import api_log

router = APIRouter()


# Schemas
class FactorEvaluationRequest(BaseModel):
    """因子評估請求"""
    factor_id: int = Field(..., description="因子 ID")
    stock_pool: str = Field("all", description="股票池（all, top100）")
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")


class FactorEvaluationResponse(BaseModel):
    """因子評估響應"""
    factor_id: int
    stock_pool: str
    start_date: str
    end_date: str

    # 因子指標
    ic: float = Field(..., description="Information Coefficient")
    icir: float = Field(..., description="IC Information Ratio")
    rank_ic: float = Field(..., description="Rank IC")
    rank_icir: float = Field(..., description="Rank ICIR")

    # 回測指標
    sharpe_ratio: float = Field(..., description="Sharpe Ratio")
    annual_return: float = Field(..., description="年化報酬率")
    max_drawdown: float = Field(..., description="最大回撤")
    win_rate: float = Field(..., description="勝率")

    # 元數據
    n_stocks: int = Field(..., description="股票數量")
    n_periods: int = Field(..., description="時間段數量")

    class Config:
        from_attributes = True


class FactorEvaluationHistoryResponse(BaseModel):
    """因子評估歷史響應"""
    id: int
    factor_id: int
    stock_pool: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]

    ic: Optional[float]
    icir: Optional[float]
    rank_ic: Optional[float]
    rank_icir: Optional[float]

    sharpe_ratio: Optional[float]
    annual_return: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]

    created_at: str

    class Config:
        from_attributes = True


@router.post("/evaluate", response_model=FactorEvaluationResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")  # 每小時最多 5 次評估（計算密集）
async def evaluate_factor(
    request: Request,
    eval_request: FactorEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    評估單個因子的績效

    計算以下指標：
    - IC (Information Coefficient)
    - ICIR (IC Information Ratio)
    - Rank IC / Rank ICIR
    - Sharpe Ratio
    - 年化報酬率
    - 最大回撤
    - 勝率
    """
    try:
        # 初始化 Service
        service = FactorEvaluationService(db)

        # 檢查因子是否存在且屬於當前用戶（使用 Service 層權限檢查）
        try:
            service.check_factor_access(eval_request.factor_id, current_user.id)
        except ValueError as e:
            api_log.log_operation(
                "evaluate_factor",
                "factor_evaluation",
                eval_request.factor_id,
                current_user.id,
                success=False,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )

        # 執行評估
        results = service.evaluate_factor(
            factor_id=eval_request.factor_id,
            stock_pool=eval_request.stock_pool,
            start_date=eval_request.start_date,
            end_date=eval_request.end_date,
            save_to_db=True
        )

        api_log.log_operation(
            "evaluate_factor",
            "factor_evaluation",
            eval_request.factor_id,
            current_user.id,
            success=True,
            metadata={"ic": results.get("ic"), "sharpe": results.get("sharpe_ratio")}
        )

        return FactorEvaluationResponse(
            factor_id=eval_request.factor_id,
            **results
        )

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "evaluate_factor",
            "factor_evaluation",
            eval_request.factor_id,
            current_user.id,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"評估失敗: {str(e)}"
        )


@router.get("/factor/{factor_id}/evaluations", response_model=List[FactorEvaluationHistoryResponse])
async def get_factor_evaluations(
    factor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取因子的評估歷史
    """
    try:
        # 初始化 Service
        service = FactorEvaluationService(db)

        # 檢查因子是否存在且屬於當前用戶（使用 Service 層權限檢查）
        try:
            service.check_factor_access(factor_id, current_user.id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )

        # 獲取評估歷史
        evaluations = service.get_factor_evaluations(factor_id)

        return [
            FactorEvaluationHistoryResponse(
                id=eval.id,
                factor_id=eval.factor_id,
                stock_pool=eval.stock_pool,
                start_date=eval.start_date,
                end_date=eval.end_date,
                ic=eval.ic,
                icir=eval.icir,
                rank_ic=eval.rank_ic,
                rank_icir=eval.rank_icir,
                sharpe_ratio=eval.sharpe_ratio,
                annual_return=eval.annual_return,
                max_drawdown=eval.max_drawdown,
                win_rate=eval.win_rate,
                created_at=eval.created_at.isoformat()
            )
            for eval in evaluations
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取評估歷史失敗: {str(e)}"
        )


@router.get("/evaluation/{evaluation_id}", response_model=FactorEvaluationHistoryResponse)
async def get_evaluation_detail(
    evaluation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    獲取單個評估的詳細資訊
    """
    try:
        # 初始化 Service
        service = FactorEvaluationService(db)

        # 檢查評估記錄權限（使用 Service 層權限檢查）
        try:
            evaluation = service.check_evaluation_access(evaluation_id, current_user.id)
        except ValueError as e:
            # 根據錯誤訊息決定狀態碼
            if "不存在" in str(e):
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_403_FORBIDDEN
            raise HTTPException(status_code=status_code, detail=str(e))

        return FactorEvaluationHistoryResponse(
            id=evaluation.id,
            factor_id=evaluation.factor_id,
            stock_pool=evaluation.stock_pool,
            start_date=evaluation.start_date,
            end_date=evaluation.end_date,
            ic=evaluation.ic,
            icir=evaluation.icir,
            rank_ic=evaluation.rank_ic,
            rank_icir=evaluation.rank_icir,
            sharpe_ratio=evaluation.sharpe_ratio,
            annual_return=evaluation.annual_return,
            max_drawdown=evaluation.max_drawdown,
            win_rate=evaluation.win_rate,
            created_at=evaluation.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取評估詳情失敗: {str(e)}"
        )


@router.delete("/evaluation/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
    evaluation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    刪除評估記錄
    """
    try:
        # 初始化 Service
        service = FactorEvaluationService(db)

        # 檢查評估記錄權限（使用 Service 層權限檢查）
        try:
            evaluation = service.check_evaluation_access(evaluation_id, current_user.id)
        except ValueError as e:
            # 根據錯誤訊息決定狀態碼
            if "不存在" in str(e):
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_403_FORBIDDEN
            raise HTTPException(status_code=status_code, detail=str(e))

        # 刪除評估記錄（使用 Service 層）
        service.delete_evaluation(evaluation)

        api_log.log_operation(
            "delete",
            "factor_evaluation",
            evaluation_id,
            current_user.id,
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        api_log.log_operation(
            "delete",
            "factor_evaluation",
            evaluation_id,
            current_user.id,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除失敗: {str(e)}"
        )


# IC 衰減分析相關 Schemas
class ICDecayRequest(BaseModel):
    """IC 衰減分析請求"""
    factor_id: int = Field(..., description="因子 ID")
    stock_pool: str = Field("all", description="股票池（all, top100）")
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")
    max_lag: int = Field(20, ge=1, le=60, description="最大滯後期（天數），預設 20，最大 60")


class ICDecayResponse(BaseModel):
    """IC 衰減分析響應"""
    factor_id: int
    factor_name: str
    lags: List[int] = Field(..., description="滯後期列表（天數）")
    ic_values: List[float] = Field(..., description="對應每個滯後期的 IC 值")
    rank_ic_values: List[float] = Field(..., description="對應每個滯後期的 Rank IC 值")
    n_stocks: int = Field(..., description="股票數量")
    n_periods: int = Field(..., description="時間段數量")
    start_date: str
    end_date: str


@router.post("/ic-decay", response_model=ICDecayResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/hour")  # 每小時最多 10 次分析（計算密集）
async def analyze_ic_decay(
    request: Request,
    decay_request: ICDecayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    分析因子 IC 衰減

    計算因子在不同持有期（滯後期）下的 IC 值，觀察因子預測能力的衰減情況。

    **用途**：
    - 評估因子的有效期（因子信號能持續多久）
    - 識別因子的最佳持有期
    - 分析因子預測能力隨時間的變化

    **解讀**：
    - IC 值接近 0：因子在該持有期沒有預測能力
    - IC 值快速衰減：因子是短期因子
    - IC 值緩慢衰減：因子是長期因子
    - IC 值穩定：因子預測能力持久
    """
    try:
        # 初始化 Service
        service = FactorEvaluationService(db)

        # 檢查因子是否存在且屬於當前用戶（使用 Service 層權限檢查）
        try:
            service.check_factor_access(decay_request.factor_id, current_user.id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )

        # 執行 IC 衰減分析
        result = service.analyze_ic_decay(
            factor_id=decay_request.factor_id,
            stock_pool=decay_request.stock_pool,
            start_date=decay_request.start_date,
            end_date=decay_request.end_date,
            max_lag=decay_request.max_lag
        )

        # 記錄操作日誌
        api_log.log_operation(
            "ic_decay",
            "factor_evaluation",
            decay_request.factor_id,
            current_user.id,
            success=True,
            max_lag=decay_request.max_lag
        )

        return ICDecayResponse(
            factor_id=decay_request.factor_id,
            factor_name=result["factor_name"],
            lags=result["lags"],
            ic_values=result["ic_values"],
            rank_ic_values=result["rank_ic_values"],
            n_stocks=result["n_stocks"],
            n_periods=result["n_periods"],
            start_date=result["start_date"],
            end_date=result["end_date"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IC decay analysis failed: {str(e)}", exc_info=True)

        api_log.log_operation(
            "ic_decay",
            "factor_evaluation",
            decay_request.factor_id,
            current_user.id,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"IC 衰減分析失敗: {str(e)}"
        )


# 快取管理端點
class CacheClearResponse(BaseModel):
    """快取清除響應"""
    success: bool
    message: str
    cleared_count: int


@router.delete("/cache/factor/{factor_id}", response_model=CacheClearResponse)
async def clear_factor_evaluation_cache(
    factor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    清除特定因子的所有評估快取

    使用場景：
    - 因子公式更新後，需要清除舊的評估結果
    - 手動觸發重新評估前，清除快取確保獲得最新結果

    權限：
    - 只能清除自己擁有的因子的快取
    """
    try:
        # 初始化 Service
        service = FactorEvaluationService(db)

        # 檢查因子是否存在且屬於當前用戶
        try:
            service.check_factor_access(factor_id, current_user.id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )

        # 清除快取
        cleared_count = service.clear_evaluation_cache(factor_id)

        api_log.log_operation(
            "clear_cache",
            "factor_evaluation",
            factor_id,
            current_user.id,
            success=True,
            metadata={"cleared_count": cleared_count}
        )

        return CacheClearResponse(
            success=True,
            message=f"成功清除因子 {factor_id} 的 {cleared_count} 個快取項目",
            cleared_count=cleared_count
        )

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "clear_cache",
            "factor_evaluation",
            factor_id,
            current_user.id,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除快取失敗: {str(e)}"
        )


@router.delete("/cache/all", response_model=CacheClearResponse)
async def clear_all_evaluation_cache(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    清除所有評估快取（僅管理員）

    使用場景：
    - 系統維護
    - 數據更新後需要重新評估所有因子
    - 清理舊快取釋放 Redis 記憶體

    權限：
    - 僅系統管理員可以執行此操作
    """
    try:
        # 檢查管理員權限
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="僅管理員可以清除所有快取"
            )

        # 初始化 Service
        service = FactorEvaluationService(db)

        # 清除所有快取
        cleared_count = service.clear_all_evaluation_cache()

        api_log.log_operation(
            "clear_all_cache",
            "factor_evaluation",
            None,
            current_user.id,
            success=True,
            metadata={"cleared_count": cleared_count}
        )

        return CacheClearResponse(
            success=True,
            message=f"成功清除所有評估快取，共 {cleared_count} 個項目",
            cleared_count=cleared_count
        )

    except HTTPException:
        raise
    except Exception as e:
        api_log.log_operation(
            "clear_all_cache",
            "factor_evaluation",
            None,
            current_user.id,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除快取失敗: {str(e)}"
        )
