#!/usr/bin/env python3
"""Manually write option factors to Qlib for testing"""

import numpy as np
import pandas as pd
from pathlib import Path
import qlib
from qlib.data.storage.file_storage import FileFeatureStorage

# Initialize Qlib
qlib.init(provider_uri='/data/qlib/tw_stock_v2')

# Create directory
Path('/data/qlib/tw_stock_v2/features/tx').mkdir(parents=True, exist_ok=True)

# Generate some test data
dates = pd.date_range('2024-10-01', '2024-12-15', freq='B')  # Business days
pcr_values = np.random.uniform(0.7, 1.5, len(dates)).astype(np.float32)
atm_iv_values = np.random.uniform(10.0, 25.0, len(dates)).astype(np.float32)

# Write PCR
print(f"Writing {len(dates)} PCR values...")
storage = FileFeatureStorage(
    instrument='tx',
    field='pcr',
    freq='day',
    provider_uri='/data/qlib/tw_stock_v2'
)
storage.write(pcr_values, index=pd.DatetimeIndex(dates))
print("✅ PCR written")

# Write ATM IV
print(f"Writing {len(dates)} ATM IV values...")
storage = FileFeatureStorage(
    instrument='tx',
    field='atm_iv',
    freq='day',
    provider_uri='/data/qlib/tw_stock_v2'
)
storage.write(atm_iv_values, index=pd.DatetimeIndex(dates))
print("✅ ATM IV written")

# Also need close price for TX
print("Also writing close prices for TX...")
close_prices = np.random.uniform(18000, 20000, len(dates)).astype(np.float32)
storage = FileFeatureStorage(
    instrument='tx',
    field='close',
    freq='day',
    provider_uri='/data/qlib/tw_stock_v2'
)
storage.write(close_prices, index=pd.DatetimeIndex(dates))
print("✅ Close prices written")

print("\nVerifying data...")
from qlib.data import D
df = D.features(['tx'], ['$pcr', '$atm_iv', '$close'], freq='day')
print(df.head(10))
print(f"\nTotal records: {len(df)}")
