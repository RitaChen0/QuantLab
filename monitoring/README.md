# QuantLab 監控系統

完整的 Prometheus + Grafana 監控解決方案

---

## 快速開始

```bash
# 啟動監控服務（推薦）
./start-monitoring.sh

# 訪問 Grafana Dashboard
open http://localhost:3001
# 預設帳號：admin / admin123
```

---

## 系統組件

| 組件 | 說明 | 端口 |
|------|------|------|
| **Prometheus** | 時序數據庫，收集 metrics | 9090 |
| **Grafana** | 數據可視化 Dashboard | 3001 |
| **Celery Exporter** | Celery 任務指標導出 | 9808 |
| **Backend Metrics** | FastAPI 自定義 metrics | 8000 |

---

## 目錄結構

```
monitoring/
├── README.md                          # 本文件
├── prometheus.yml                      # Prometheus 配置
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml         # Grafana 數據源配置
│   │   └── dashboards/
│   │       └── default.yml            # Dashboard provisioning 配置
│   └── dashboards/
│       └── quantlab-overview.json     # QuantLab 預設 Dashboard
```

---

## 預設 Dashboard

### QuantLab - Celery Monitoring

自動配置的 Celery 監控 Dashboard，包含：

1. **Celery Workers & Active Tasks** - Worker 數量和活躍任務
2. **Total Tasks Processed** - 累計處理任務數
3. **Failed Tasks** - 失敗任務數（監控系統健康）
4. **Task Processing Rate** - 任務處理速率（tasks/sec）
5. **Average Task Runtime** - 平均任務執行時間
6. **Queue Length by Queue** - 各隊列等待任務數

---

## Metrics 端點

### Backend Metrics (http://localhost:8000/metrics)

暴露的自定義 metrics：

```promql
# API 請求總數
quantlab_api_requests_total{method="GET",endpoint="/api/v1/backtest",status="200"}

# API 響應時間
quantlab_api_response_time_seconds_bucket{method="POST",endpoint="/api/v1/backtest/run"}

# 回測總數
quantlab_backtests_total{status="completed"}

# 策略總數
quantlab_strategies_total

# 活躍用戶數
quantlab_active_users

# 資料庫連接數
quantlab_db_connections
```

### Celery Metrics (http://localhost:9808/metrics)

由 celery-exporter 提供：

```promql
# Worker 數量
celery_workers

# 活躍任務數
celery_tasks_active_total

# 任務總數（按狀態分組）
celery_tasks_total{state="SUCCESS"}
celery_tasks_total{state="FAILURE"}

# 任務執行時間
celery_task_runtime_seconds_sum
celery_task_runtime_seconds_count

# 隊列長度
celery_queue_length{queue="backtest"}
```

---

## 常用命令

```bash
# 查看日誌
docker compose logs -f prometheus
docker compose logs -f grafana
docker compose logs -f celery-exporter

# 重啟服務
docker compose restart prometheus grafana celery-exporter

# 停止服務
docker compose stop prometheus grafana celery-exporter

# 完全清理（包括數據）
docker compose down -v
```

---

## 完整文檔

詳細使用指南請參考：
- [Prometheus + Grafana 完整指南](../PROMETHEUS_GRAFANA_GUIDE.md)
- [監控與自動化測試指南](../MONITORING_AND_TESTING_GUIDE.md)

---

**版本**: v1.0
**最後更新**: 2025-12-11
