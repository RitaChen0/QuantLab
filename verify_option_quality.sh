#!/bin/bash
# 選擇權數據品質驗證腳本

echo "🔍 驗證選擇權數據品質..."
echo ""

docker compose exec postgres psql -U quantlab quantlab << 'SQL'
-- 1. 整體統計
\echo '===== 1. 整體數據統計 ====='
SELECT 
    COUNT(*) as total_records,
    COUNT(avg_call_delta) as records_with_greeks,
    ROUND(COUNT(avg_call_delta) * 100.0 / COUNT(*), 1) as greeks_percentage,
    MIN(date) as earliest,
    MAX(date) as latest
FROM option_daily_factors
WHERE underlying_id = 'TX';

-- 2. Delta 分佈檢查（真實計算應該有較大變異）
\echo ''
\echo '===== 2. Delta 值分佈 ====='
SELECT 
    MIN(avg_call_delta) as min_call_delta,
    MAX(avg_call_delta) as max_call_delta,
    AVG(avg_call_delta) as avg_call_delta,
    STDDEV(avg_call_delta) as stddev_call_delta
FROM option_daily_factors
WHERE underlying_id = 'TX'
  AND avg_call_delta IS NOT NULL;

-- 3. 估算值檢測
\echo ''
\echo '===== 3. 估算值比例 ====='
SELECT 
    SUM(CASE WHEN ABS((avg_call_delta - 0.5) / NULLIF(atm_iv, 0) - 0.10) < 0.001 THEN 1 ELSE 0 END) as estimated_count,
    COUNT(*) as total_count,
    ROUND(SUM(CASE WHEN ABS((avg_call_delta - 0.5) / NULLIF(atm_iv, 0) - 0.10) < 0.001 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as estimated_percentage
FROM option_daily_factors
WHERE underlying_id = 'TX'
  AND avg_call_delta IS NOT NULL;

-- 4. 最近 5 天數據樣本
\echo ''
\echo '===== 4. 最近 5 天數據樣本 ====='
SELECT 
    date,
    ROUND(avg_call_delta::numeric, 4) as call_delta,
    ROUND(avg_put_delta::numeric, 4) as put_delta,
    ROUND(gamma_exposure::numeric, 1) as gamma,
    data_quality_score
FROM option_daily_factors
WHERE underlying_id = 'TX'
ORDER BY date DESC
LIMIT 5;
SQL

echo ""
echo "✅ 驗證完成"
echo ""
echo "📌 品質判斷標準："
echo "  - stddev_call_delta > 0.01：數據有合理變異（真實計算）"
echo "  - estimated_percentage < 5%：估算值比例低"
echo "  - data_quality_score > 0.8：數據品質良好"
