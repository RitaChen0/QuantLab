#!/usr/bin/env python3
"""Test FinMind API for institutional investors"""
import sys
sys.path.insert(0, '/app')

from app.services.finmind_client import FinMindClient
from app.db.session import SessionLocal, ensure_models_imported
from datetime import date

# Ensure models are imported
ensure_models_imported()

print("Testing FinMind API...")
client = FinMindClient()

# Test API call
print("\n1. Fetching data from FinMind API for 2330...")
df = client.get_institutional_investors('2330', '2024-12-01', '2024-12-13')

print(f"✅ Retrieved {len(df)} records")
print("\nSample data:")
print(df.head(10))

# Test direct database insert
print("\n2. Testing direct database insert...")
from app.models.institutional_investor import InstitutionalInvestor
import pandas as pd

db = SessionLocal()
try:
    # Insert one record directly
    if len(df) > 0:
        row = df.iloc[0]
        record = InstitutionalInvestor(
            date=pd.to_datetime(row['date']).date(),
            stock_id=row['stock_id'],
            investor_type=row['name'],
            buy_volume=int(row['buy']),
            sell_volume=int(row['sell'])
        )
        db.add(record)
        db.commit()
        print(f"✅ Inserted record: {record}")

        # Query it back
        count = db.query(InstitutionalInvestor).count()
        print(f"✅ Total records in database: {count}")
    else:
        print("⚠️ No data to insert")
finally:
    db.close()

print("\n✅ All tests passed!")
