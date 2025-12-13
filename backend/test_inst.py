#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

from app.db.session import SessionLocal, ensure_models_imported
from app.services.institutional_investor_service import InstitutionalInvestorService
from app.schemas.institutional_investor import InvestorType
from datetime import date

# Ensure all models are imported
ensure_models_imported()

db = SessionLocal()
service = InstitutionalInvestorService(db)

print("Testing institutional investor sync...")
result = service.sync_stock_data('2330', '2024-12-01', '2024-12-13')
print(f"Status: {result['status']}")
print(f"Inserted: {result.get('inserted', 0)}")
print(f"Updated: {result.get('updated', 0)}")

print("\nQuerying summary...")
summary = service.get_summary('2330', date(2024, 12, 13))
print(f"Foreign net: {summary.foreign_net:,}")
print(f"Trust net: {summary.trust_net:,}")
print(f"Total net: {summary.total_net:,}")

db.close()
print("\nTest completed!")
