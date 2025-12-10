"""
從 FinLab API 匯入完整的股票產業分類資料

此腳本會:
1. 從 FinLab 取得 company_basic_info 資料集
2. 提取股票代號和產業類別
3. 將 FinLab 產業名稱對應到 TWSE 產業代碼
4. 批次匯入到 stock_industries 資料表
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.base import import_models
from app.models.industry import Industry
from app.models.stock_industry import StockIndustry
from app.models.stock import Stock
from app.core.config import settings
from loguru import logger

try:
    import finlab
    from finlab import data
    import pandas as pd
    FINLAB_AVAILABLE = True
except ImportError:
    FINLAB_AVAILABLE = False
    logger.error("FinLab package not installed")
    sys.exit(1)

# Import all models
import_models()


# FinLab 產業名稱到 TWSE 產業代碼對應表
INDUSTRY_MAPPING = {
    # Level 1 - 主要產業
    "水泥工業": "M01",
    "食品工業": "M02",
    "塑膠工業": "M03",
    "紡織纖維": "M04",
    "電機機械": "M05",
    "電器電纜": "M06",
    "化學工業": "M07",
    "生技醫療業": "M07",  # 歸類到化學生技醫療
    "玻璃陶瓷": "M08",
    "造紙工業": "M09",
    "鋼鐵工業": "M10",
    "橡膠工業": "M11",
    "汽車工業": "M12",
    "建材營造": "M14",
    "航運業": "M15",
    "觀光餐旅": "M16",  # 歸類到觀光事業
    "觀光事業": "M16",
    "金融保險業": "M17",
    "金融業": "M17",
    "貿易百貨": "M18",
    "綜合企業": "M19",
    "文化創意業": "M21",
    "農業科技": "M22",
    "電子商務": "M23",

    # Level 2 - 電子工業細分
    "半導體業": "M1301",
    "電腦及週邊設備業": "M1302",
    "光電業": "M1303",
    "通信網路業": "M1304",
    "電子零組件業": "M1305",
    "電子通路業": "M1306",
    "資訊服務業": "M1307",
    "其他電子業": "M1308",
    "數位雲端": "M1307",  # 歸類到資訊服務

    # Level 2 - 金融保險細分
    "銀行業": "M1701",
    "證券業": "M1702",
    "保險業": "M1703",
    "金融控股": "M1704",

    # 特殊分類
    "其他": "M20",
    "綠能環保": "M20",  # 暫時歸類到其他
    "居家生活": "M20",
    "運動休閒": "M20",
    "油電燃氣業": "M20",
}


def get_finlab_industry_data():
    """從 FinLab 取得產業分類資料"""
    logger.info("正在從 FinLab 取得產業分類資料...")

    if not FINLAB_AVAILABLE:
        raise RuntimeError("FinLab package not available")

    # Login to FinLab
    api_token = settings.FINLAB_API_TOKEN
    if not api_token:
        raise RuntimeError("FINLAB_API_TOKEN not configured")

    finlab.login(api_token)
    logger.info("✅ FinLab 登入成功")

    # Get company basic info
    basic_info = data.get('company_basic_info')
    logger.info(f"✅ 取得 {len(basic_info)} 筆公司資料")

    # Extract relevant columns
    industry_data = basic_info[['stock_id', '產業類別', '公司簡稱']].copy()

    # Remove rows with missing industry
    industry_data = industry_data.dropna(subset=['產業類別'])

    logger.info(f"✅ 有效資料: {len(industry_data)} 筆")
    logger.info(f"產業類別數: {industry_data['產業類別'].nunique()}")

    return industry_data


def map_finlab_to_twse_industry(finlab_industry: str) -> str:
    """
    將 FinLab 產業名稱對應到 TWSE 產業代碼

    Args:
        finlab_industry: FinLab 產業名稱

    Returns:
        TWSE 產業代碼 (e.g., "M01", "M1301")
    """
    # Direct mapping
    if finlab_industry in INDUSTRY_MAPPING:
        return INDUSTRY_MAPPING[finlab_industry]

    # Fallback to M20 (其他)
    logger.warning(f"未找到對應的產業代碼: {finlab_industry}, 使用 M20 (其他)")
    return "M20"


def import_stock_industries(db: Session, industry_data: pd.DataFrame, clear_existing: bool = False):
    """
    匯入股票產業分類到資料庫

    Args:
        db: Database session
        industry_data: DataFrame with columns [stock_id, 產業類別, 公司簡稱]
        clear_existing: Whether to clear existing mappings
    """
    logger.info("開始匯入股票產業分類...")

    # Clear existing mappings if requested
    if clear_existing:
        existing_count = db.query(StockIndustry).count()
        if existing_count > 0:
            logger.warning(f"清除現有的 {existing_count} 筆產業分類資料...")
            db.query(StockIndustry).delete()
            db.commit()
            logger.info("✅ 已清除現有資料")

    # Statistics
    created_count = 0
    skipped_no_stock = 0
    skipped_no_industry = 0
    skipped_duplicate = 0
    industry_stats = {}

    # Process each stock
    for idx, row in industry_data.iterrows():
        stock_id = str(row['stock_id'])
        finlab_industry = row['產業類別']
        company_name = row['公司簡稱']

        # Check if stock exists in database
        stock = db.query(Stock).filter(Stock.stock_id == stock_id).first()
        if not stock:
            skipped_no_stock += 1
            if skipped_no_stock <= 10:  # Only log first 10
                logger.debug(f"股票不存在: {stock_id} ({company_name})")
            continue

        # Map to TWSE industry code
        industry_code = map_finlab_to_twse_industry(finlab_industry)

        # Check if industry exists
        industry = db.query(Industry).filter(Industry.code == industry_code).first()
        if not industry:
            skipped_no_industry += 1
            logger.warning(f"產業代碼不存在: {industry_code} (來自: {finlab_industry})")
            continue

        # Check if mapping already exists
        existing = db.query(StockIndustry).filter(
            StockIndustry.stock_id == stock_id,
            StockIndustry.industry_code == industry_code
        ).first()

        if existing:
            skipped_duplicate += 1
            continue

        # Create mapping
        mapping = StockIndustry(
            stock_id=stock_id,
            industry_code=industry_code,
            is_primary=True
        )
        db.add(mapping)
        created_count += 1

        # Track statistics
        industry_stats[industry_code] = industry_stats.get(industry_code, 0) + 1

        # Commit in batches of 100
        if created_count % 100 == 0:
            db.commit()
            logger.info(f"已匯入 {created_count} 筆...")

    # Final commit
    db.commit()

    # Log results
    logger.info("=" * 60)
    logger.info("匯入完成!")
    logger.info(f"✅ 成功匯入: {created_count} 筆")
    logger.info(f"⚠️  略過 (股票不存在): {skipped_no_stock} 筆")
    logger.info(f"⚠️  略過 (產業不存在): {skipped_no_industry} 筆")
    logger.info(f"⚠️  略過 (重複): {skipped_duplicate} 筆")

    # Show top industries
    logger.info("\n各產業股票數量 (Top 15):")
    sorted_industries = sorted(industry_stats.items(), key=lambda x: x[1], reverse=True)
    for code, count in sorted_industries[:15]:
        industry = db.query(Industry).filter(Industry.code == code).first()
        industry_name = industry.name_zh if industry else "Unknown"
        logger.info(f"  {code} ({industry_name}): {count} 檔")

    logger.info("=" * 60)


def verify_import(db: Session):
    """驗證匯入結果"""
    logger.info("\n驗證匯入結果...")

    # Total mappings
    total_mappings = db.query(StockIndustry).count()
    logger.info(f"總股票-產業對應數: {total_mappings}")

    # Check cement industry (M01)
    cement_stocks = db.query(StockIndustry).filter(
        StockIndustry.industry_code == "M01"
    ).all()

    logger.info(f"\n水泥工業 (M01) 股票數: {len(cement_stocks)}")
    if cement_stocks:
        logger.info("水泥工業股票:")
        for mapping in cement_stocks:
            stock = db.query(Stock).filter(Stock.stock_id == mapping.stock_id).first()
            stock_name = stock.name if stock else "Unknown"
            logger.info(f"  - {mapping.stock_id} {stock_name}")

    # Check semiconductor industry (M1301)
    semi_stocks = db.query(StockIndustry).filter(
        StockIndustry.industry_code == "M1301"
    ).all()

    logger.info(f"\n半導體業 (M1301) 股票數: {len(semi_stocks)}")
    logger.info(f"半導體業樣本股票 (前 10 檔):")
    for mapping in semi_stocks[:10]:
        stock = db.query(Stock).filter(Stock.stock_id == mapping.stock_id).first()
        stock_name = stock.name if stock else "Unknown"
        logger.info(f"  - {mapping.stock_id} {stock_name}")


def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("FinLab 產業分類資料匯入工具")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # Step 1: Get data from FinLab
        industry_data = get_finlab_industry_data()

        # Step 2: Import to database
        logger.info("\n" + "=" * 60)
        import_stock_industries(
            db,
            industry_data,
            clear_existing=True  # Clear existing data
        )

        # Step 3: Verify import
        logger.info("\n" + "=" * 60)
        verify_import(db)

        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有操作完成!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 錯誤: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
