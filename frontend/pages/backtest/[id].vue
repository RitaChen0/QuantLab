<style scoped lang="scss">
.dashboard-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-container {
  width: 100%;
}

.back-button-container {
  margin-bottom: 2rem;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
    border-color: #3b82f6;
    color: #3b82f6;
  }
}

.loading-state {
  text-align: center;
  padding: 4rem 2rem;

  .spinner {
    width: 3rem;
    height: 3rem;
    border: 4px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  margin-bottom: 1rem;
}

.backtest-detail {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.info-card,
.metrics-card,
.trades-card {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 1.5rem 0;
}

// 交易圖表樣式
.trade-chart-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;

  h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
  }
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  color: #3b82f6;
  border: 1px solid #3b82f6;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: #3b82f6;
    color: white;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.trade-chart-canvas {
  width: 100%;
  height: 600px;  // 增加高度以容納縮放控制條
  background: white;
  border-radius: 0.5rem;
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #6b7280;

  .spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }
}

.chart-error {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  text-align: center;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  background: white;
  border-radius: 0.5rem;
  border: 2px dashed #e5e7eb;
  color: #6b7280;

  .placeholder-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  p {
    margin: 0;
    font-size: 0.875rem;
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 0.5rem;

  .info-label {
    color: #6b7280;
    font-weight: 500;
  }

  .info-value {
    color: #111827;
    font-weight: 600;
  }
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  font-weight: 500;

  &.status-pending {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.status-running {
    background: #fef3c7;
    color: #92400e;
  }

  &.status-completed {
    background: #d1fae5;
    color: #065f46;
  }

  &.status-failed {
    background: #fee2e2;
    color: #991b1b;
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.metric-item {
  text-align: center;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.75rem;
  border: 2px solid #e5e7eb;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    transform: translateY(-2px);
  }

  .metric-label {
    color: #6b7280;
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
  }

  .metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #111827;

    &.positive {
      color: #059669;
    }

    &.negative {
      color: #dc2626;
    }
  }
}

.trades-table-container {
  overflow-x: auto;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;

  th {
    background: #f9fafb;
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    color: #374151;
    border-bottom: 2px solid #e5e7eb;
  }

  td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e5e7eb;
    color: #111827;
  }

  tr:hover {
    background: #f9fafb;
  }
}

.trade-type {
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;

  &.buy {
    background: #d1fae5;
    color: #065f46;
  }

  &.sell {
    background: #fee2e2;
    color: #991b1b;
  }
}

.pnl {
  font-weight: 600;

  &.positive {
    color: #059669;
  }

  &.negative {
    color: #dc2626;
  }
}

@media (max-width: 768px) {
      .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .trades-table {
    font-size: 0.875rem;

    th, td {
      padding: 0.5rem;
    }
  }
}

/* 引擎徽章樣式 */
.engine-badge {
  font-size: 0.875rem;
  padding: 0.375rem 0.875rem;
  border-radius: 16px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.engine-badge.backtrader {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.engine-badge.qlib {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

/* ===== 視覺化圖表樣式 ===== */
.charts-container {
  margin-top: 2rem;
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tabs-nav {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
  margin-bottom: 1.5rem;
  overflow-x: auto;

  /* 滾動條樣式 */
  &::-webkit-scrollbar {
    height: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 2px;
  }
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #6b7280;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  margin-bottom: -2px;

  &:hover {
    color: #3b82f6;
    background: #eff6ff;
  }

  &.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
    font-weight: 600;
  }
}

.tab-content {
  min-height: 400px;
}

.chart-panel {
  animation: fadeIn 0.3s ease-in-out;
}

.chart-canvas {
  width: 100%;
  height: 500px;
  min-height: 400px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 響應式調整 */
@media (max-width: 768px) {
  .charts-container {
    padding: 1rem;
  }

  .chart-canvas {
    height: 350px;
    min-height: 300px;
  }

  .tab-button {
    padding: 0.5rem 0.875rem;
    font-size: 0.8125rem;
  }
}
</style>