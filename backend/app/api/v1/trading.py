"""
Trading API Routes
Handles broker integration and order management
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/brokers")
async def list_brokers():
    """取得支援券商列表"""
    return {"message": "券商列表功能開發中"}


@router.post("/connect")
async def connect_broker():
    """連接券商"""
    return {"message": "連接券商功能開發中"}


@router.get("/positions")
async def get_positions():
    """取得持倉"""
    return {"message": "取得持倉功能開發中"}


@router.post("/orders")
async def create_order():
    """下單"""
    return {"message": "下單功能開發中"}


@router.get("/orders")
async def list_orders():
    """取得訂單列表"""
    return {"message": "訂單列表功能開發中"}


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """取消訂單"""
    return {"message": f"取消訂單 {order_id} 功能開發中"}
