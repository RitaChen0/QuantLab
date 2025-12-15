#!/usr/bin/env python3
"""Create Qlib option data files manually"""

import numpy as np
import pandas as pd
from pathlib import Path
import struct

# Create directory
qlib_dir = Path('/data/qlib/tw_stock_v2/features/tx')
qlib_dir.mkdir(parents=True, exist_ok=True)

# Generate test data
dates = pd.date_range('2024-10-01', '2024-12-15', freq='B')  # 54 business days
num_days = len(dates)

print(f"Creating {num_days} days of data...")

# Generate realistic PCR values (0.7 - 1.5)
np.random.seed(42)
pcr_values = np.random.uniform(0.7, 1.5, num_days).astype(np.float32)

# Generate realistic ATM IV values (10 - 25%)
atm_iv_values = np.random.uniform(10.0, 25.0, num_days).astype(np.float32)

# Generate realistic close prices (18000 - 20000)
close_values = np.random.uniform(18000, 20000, num_days).astype(np.float32)

# Write binary files in Qlib format
# Qlib format: 4 bytes (start_index) + data as float32

def write_qlib_bin(filepath, data):
    """Write Qlib binary file"""
    with open(filepath, 'wb') as f:
        # Write start index (calendar index of first date)
        # For simplicity, use 0
        f.write(struct.pack('<f', 0.0))
        # Write all data
        data.tofile(f)
    print(f"  ✅ Written: {filepath.name} ({len(data)} values)")

# Write PCR
write_qlib_bin(qlib_dir / 'pcr.day.bin', pcr_values)

# Write ATM IV
write_qlib_bin(qlib_dir / 'atm_iv.day.bin', atm_iv_values)

# Write close prices
write_qlib_bin(qlib_dir / 'close.day.bin', close_values)

print(f"\n✅ Created Qlib option data in {qlib_dir}")
print(f"Files:")
for f in sorted(qlib_dir.glob('*.bin')):
    size = f.stat().st_size
    print(f"  - {f.name}: {size} bytes")
