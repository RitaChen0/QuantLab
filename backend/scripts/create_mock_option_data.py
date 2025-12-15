#!/usr/bin/env python3
"""
Create mock option data for testing

Creates realistic option factors for TX for the past 90 days
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, timedelta
import random
from decimal import Decimal
from app.db.session import get_db
from app.repositories.option import OptionDailyFactorRepository
from app.schemas.option import OptionDailyFactorCreate
from loguru import logger

def generate_mock_factors(days=90):
    """Generate mock option factors for testing"""

    db = next(get_db())

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    logger.info(f"Creating mock option data from {start_date} to {end_date}")

    current_date = start_date
    count = 0

    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        # Generate realistic PCR values (0.6 - 1.8, centered around 1.0)
        base_pcr = 1.0
        pcr_noise = random.gauss(0, 0.2)  # Normal distribution
        pcr_volume = max(0.5, min(2.0, base_pcr + pcr_noise))

        # Add trend component (some periods are more bearish/bullish)
        trend_factor = 0.1 * random.choice([-1, 0, 1])
        pcr_volume += trend_factor

        # PCR OI tends to be similar but slightly different
        pcr_oi = pcr_volume + random.gauss(0, 0.1)
        pcr_oi = max(0.5, min(2.0, pcr_oi))

        # ATM IV (8% - 25%, varying based on market conditions)
        base_iv = 15.0
        iv_noise = random.gauss(0, 3.0)
        atm_iv = max(5.0, min(30.0, base_iv + iv_noise))

        # Data quality score (mostly high quality)
        quality = random.uniform(0.85, 1.0)

        # Create factor
        factor_data = OptionDailyFactorCreate(
            underlying_id='TX',
            date=current_date,
            pcr_volume=Decimal(str(round(pcr_volume, 4))),
            pcr_open_interest=Decimal(str(round(pcr_oi, 4))),
            atm_iv=Decimal(str(round(atm_iv, 4))),
            calculation_version='1.0.0',
            data_quality_score=Decimal(str(round(quality, 2)))
        )

        try:
            OptionDailyFactorRepository.upsert(db, factor_data)
            count += 1

            if count % 10 == 0:
                logger.info(f"Created {count} records...")

        except Exception as e:
            logger.error(f"Error creating record for {current_date}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"✅ Created {count} mock option factor records")

    # Display some sample data
    logger.info("\nSample data (latest 5 records):")
    recent = OptionDailyFactorRepository.get_by_underlying(
        db, 'TX', limit=5
    )

    for r in recent:
        logger.info(
            f"  {r.date}: PCR={r.pcr_volume}, ATM_IV={r.atm_iv}, Quality={r.data_quality_score}"
        )

if __name__ == '__main__':
    generate_mock_factors()
