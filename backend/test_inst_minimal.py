#!/usr/bin/env python3
"""Minimal test for institutional investor feature"""
import sys
sys.path.insert(0, '/app')

# Test 1: Ensure models are imported
print("Test 1: Ensuring all models are imported...")
from app.db.session import ensure_models_imported
ensure_models_imported()
print("✅ Models imported successfully")

# Test 2: Database query
print("\nTest 2: Querying database...")
from app.db.session import SessionLocal
from app.models.institutional_investor import InstitutionalInvestor
db = SessionLocal()
try:
    count = db.query(InstitutionalInvestor).count()
    print(f"✅ Database query successful. Record count: {count}")
finally:
    db.close()

print("\n✅ All tests passed!")
