"""
Populate industries table with Taiwan Stock Exchange (TWSE) industry classifications.

Based on TWSE official industry categories.
"""
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.base import import_models  # Import all models to resolve relationships
from app.models.industry import Industry
from app.models.stock_industry import StockIndustry
from app.models.stock import Stock
from loguru import logger
import sys

# Import all models to resolve SQLAlchemy relationships
import_models()


# TWSE Standard Industry Classifications (證交所產業分類)
INDUSTRIES = [
    # Level 1 - 大類 (Main Categories)
    {"code": "M01", "name_zh": "水泥工業", "name_en": "Cement", "level": 1, "parent_code": None},
    {"code": "M02", "name_zh": "食品工業", "name_en": "Food", "level": 1, "parent_code": None},
    {"code": "M03", "name_zh": "塑膠工業", "name_en": "Plastics", "level": 1, "parent_code": None},
    {"code": "M04", "name_zh": "紡織纖維", "name_en": "Textiles", "level": 1, "parent_code": None},
    {"code": "M05", "name_zh": "電機機械", "name_en": "Electric Machinery", "level": 1, "parent_code": None},
    {"code": "M06", "name_zh": "電器電纜", "name_en": "Electrical & Cable", "level": 1, "parent_code": None},
    {"code": "M07", "name_zh": "化學生技醫療", "name_en": "Chemical, Biotech & Medical", "level": 1, "parent_code": None},
    {"code": "M08", "name_zh": "玻璃陶瓷", "name_en": "Glass & Ceramics", "level": 1, "parent_code": None},
    {"code": "M09", "name_zh": "造紙工業", "name_en": "Paper", "level": 1, "parent_code": None},
    {"code": "M10", "name_zh": "鋼鐵工業", "name_en": "Steel", "level": 1, "parent_code": None},
    {"code": "M11", "name_zh": "橡膠工業", "name_en": "Rubber", "level": 1, "parent_code": None},
    {"code": "M12", "name_zh": "汽車工業", "name_en": "Automobile", "level": 1, "parent_code": None},
    {"code": "M13", "name_zh": "電子工業", "name_en": "Electronics", "level": 1, "parent_code": None},
    {"code": "M14", "name_zh": "建材營造", "name_en": "Construction", "level": 1, "parent_code": None},
    {"code": "M15", "name_zh": "航運業", "name_en": "Shipping", "level": 1, "parent_code": None},
    {"code": "M16", "name_zh": "觀光事業", "name_en": "Tourism", "level": 1, "parent_code": None},
    {"code": "M17", "name_zh": "金融保險", "name_en": "Financial", "level": 1, "parent_code": None},
    {"code": "M18", "name_zh": "貿易百貨", "name_en": "Trading & Department Store", "level": 1, "parent_code": None},
    {"code": "M19", "name_zh": "綜合企業", "name_en": "Conglomerate", "level": 1, "parent_code": None},
    {"code": "M20", "name_zh": "其他", "name_en": "Others", "level": 1, "parent_code": None},
    {"code": "M21", "name_zh": "文化創意業", "name_en": "Cultural & Creative", "level": 1, "parent_code": None},
    {"code": "M22", "name_zh": "農業科技", "name_en": "Agricultural Technology", "level": 1, "parent_code": None},
    {"code": "M23", "name_zh": "電子商務", "name_en": "E-commerce", "level": 1, "parent_code": None},

    # Level 2 - 電子工業細分 (Electronics Subcategories)
    {"code": "M1301", "name_zh": "半導體業", "name_en": "Semiconductor", "level": 2, "parent_code": "M13"},
    {"code": "M1302", "name_zh": "電腦及週邊設備業", "name_en": "Computer & Peripherals", "level": 2, "parent_code": "M13"},
    {"code": "M1303", "name_zh": "光電業", "name_en": "Optoelectronics", "level": 2, "parent_code": "M13"},
    {"code": "M1304", "name_zh": "通信網路業", "name_en": "Communications & Internet", "level": 2, "parent_code": "M13"},
    {"code": "M1305", "name_zh": "電子零組件業", "name_en": "Electronic Components", "level": 2, "parent_code": "M13"},
    {"code": "M1306", "name_zh": "電子通路業", "name_en": "Electronic Distribution", "level": 2, "parent_code": "M13"},
    {"code": "M1307", "name_zh": "資訊服務業", "name_en": "Information Services", "level": 2, "parent_code": "M13"},
    {"code": "M1308", "name_zh": "其他電子業", "name_en": "Other Electronics", "level": 2, "parent_code": "M13"},

    # Level 3 - 半導體細分 (Semiconductor Subcategories)
    {"code": "M130101", "name_zh": "IC設計", "name_en": "IC Design", "level": 3, "parent_code": "M1301"},
    {"code": "M130102", "name_zh": "IC製造", "name_en": "IC Manufacturing", "level": 3, "parent_code": "M1301"},
    {"code": "M130103", "name_zh": "IC封測", "name_en": "IC Packaging & Testing", "level": 3, "parent_code": "M1301"},
    {"code": "M130104", "name_zh": "IC通路", "name_en": "IC Distribution", "level": 3, "parent_code": "M1301"},
    {"code": "M130105", "name_zh": "IC其他", "name_en": "Other IC", "level": 3, "parent_code": "M1301"},

    # Level 2 - 金融保險細分 (Financial Subcategories)
    {"code": "M1701", "name_zh": "銀行業", "name_en": "Banking", "level": 2, "parent_code": "M17"},
    {"code": "M1702", "name_zh": "證券業", "name_en": "Securities", "level": 2, "parent_code": "M17"},
    {"code": "M1703", "name_zh": "保險業", "name_en": "Insurance", "level": 2, "parent_code": "M17"},
    {"code": "M1704", "name_zh": "金融控股", "name_en": "Financial Holding", "level": 2, "parent_code": "M17"},
    {"code": "M1705", "name_zh": "其他金融", "name_en": "Other Financial", "level": 2, "parent_code": "M17"},
]


# Major stock to industry mappings (台股代表性個股產業歸類)
# Format: (stock_id, industry_code, is_primary)
STOCK_INDUSTRY_MAPPINGS = [
    # 半導體業
    ("2330", "M130102", True),   # 台積電 - IC製造
    ("2303", "M130101", True),   # 聯電 - IC製造
    ("2454", "M130101", True),   # 聯發科 - IC設計
    ("2379", "M130101", True),   # 瑞昱 - IC設計
    ("3034", "M130103", True),   # 日月光投控 - IC封測
    ("2317", "M130103", True),   # 鴻海 - IC封測

    # 電腦及週邊設備業
    ("2382", "M1302", True),     # 廣達 - 電腦及週邊
    ("2357", "M1302", True),     # 華碩 - 電腦及週邊
    ("2356", "M1302", True),     # 英業達 - 電腦及週邊

    # 光電業
    ("2409", "M1303", True),     # 友達 - 光電
    ("2474", "M1303", True),     # 可成 - 光電

    # 金融業
    ("2882", "M1701", True),     # 國泰金 - 金融控股
    ("2881", "M1701", True),     # 富邦金 - 金融控股
    ("2891", "M1701", True),     # 中信金 - 金融控股
    ("2884", "M1701", True),     # 玉山金 - 金融控股
    ("2886", "M1701", True),     # 兆豐金 - 金融控股

    # 其他產業
    ("1101", "M01", True),       # 台泥 - 水泥工業
    ("1216", "M02", True),       # 統一 - 食品工業
    ("1326", "M04", True),       # 台化 - 塑膠工業
    ("2002", "M10", True),       # 中鋼 - 鋼鐵工業
    ("2412", "M1304", True),     # 中華電 - 通信網路
    ("2308", "M1302", True),     # 台達電 - 電子零組件
]


def populate_industries(db: Session) -> None:
    """Populate industries table with TWSE classifications."""
    logger.info("Starting industry population...")

    # Check if industries already exist
    existing_count = db.query(Industry).count()
    if existing_count > 0:
        logger.warning(f"Industries table already has {existing_count} records. Skipping...")
        return

    # Insert industries
    created_count = 0
    for industry_data in INDUSTRIES:
        industry = Industry(**industry_data)
        db.add(industry)
        created_count += 1

    db.commit()
    logger.info(f"✅ Created {created_count} industry records")


def populate_stock_industries(db: Session) -> None:
    """Map stocks to industries."""
    logger.info("Starting stock-industry mapping...")

    # Check if mappings already exist
    existing_count = db.query(StockIndustry).count()
    if existing_count > 0:
        logger.warning(f"Stock-industry mappings already exist ({existing_count} records). Skipping...")
        return

    # Insert mappings
    created_count = 0
    skipped_count = 0

    for stock_id, industry_code, is_primary in STOCK_INDUSTRY_MAPPINGS:
        # Check if stock exists
        stock = db.query(Stock).filter(Stock.stock_id == stock_id).first()
        if not stock:
            logger.warning(f"Stock {stock_id} not found, skipping...")
            skipped_count += 1
            continue

        # Check if industry exists
        industry = db.query(Industry).filter(Industry.code == industry_code).first()
        if not industry:
            logger.warning(f"Industry {industry_code} not found, skipping...")
            skipped_count += 1
            continue

        # Create mapping
        mapping = StockIndustry(
            stock_id=stock_id,
            industry_code=industry_code,
            is_primary=is_primary
        )
        db.add(mapping)
        created_count += 1

    db.commit()
    logger.info(f"✅ Created {created_count} stock-industry mappings (skipped {skipped_count})")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Populating Industry Classification Database")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # Step 1: Populate industries
        populate_industries(db)

        # Step 2: Map stocks to industries
        populate_stock_industries(db)

        # Summary
        total_industries = db.query(Industry).count()
        total_mappings = db.query(StockIndustry).count()

        logger.info("=" * 60)
        logger.info("Population Complete!")
        logger.info(f"Total industries: {total_industries}")
        logger.info(f"Total stock-industry mappings: {total_mappings}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during population: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
