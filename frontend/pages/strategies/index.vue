<style scoped lang="scss">
// 複用 dashboard 的通用樣式
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

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  .page-subtitle {
    color: #6b7280;
    margin: 0;
  }
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  .icon {
    font-size: 1.25rem;
  }

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

// 搜尋和篩選
.filters-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.search-box {
  margin-bottom: 1rem;

  .search-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }
}

.filter-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  color: #6b7280;
  border: 2px solid transparent;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #e5e7eb;
  }

  &.active {
    background: #dbeafe;
    color: #1e40af;
    border-color: #3b82f6;
  }
}

// 載入和錯誤狀態
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

// 策略卡片
.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.strategy-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }
}

.strategy-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
}

.strategy-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;

  &.status-draft {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.status-active {
    background: #d1fae5;
    color: #065f46;
  }

  &.status-paused {
    background: #fef3c7;
    color: #92400e;
  }

  &.status-archived {
    background: #e5e7eb;
    color: #374151;
  }
}

.strategy-description {
  color: #6b7280;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.strategy-meta {
  margin-bottom: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;

  .meta-label {
    color: #6b7280;
  }

  .meta-value {
    color: #111827;
  }
}

.strategy-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-action {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;

  &.btn-activate {
    background: #d1fae5;
    color: #065f46;

    &:hover {
      background: #a7f3d0;
    }
  }

  &.btn-pause {
    background: #fef3c7;
    color: #92400e;

    &:hover {
      background: #fde68a;
    }
  }

  &.btn-view {
    background: #dbeafe;
    color: #1e40af;

    &:hover {
      background: #bfdbfe;
    }
  }

  &.btn-edit {
    background: #fef3c7;
    color: #92400e;

    &:hover {
      background: #fde68a;
    }
  }

  &.btn-clone {
    background: #e0e7ff;
    color: #3730a3;

    &:hover {
      background: #c7d2fe;
    }
  }

  &.btn-delete {
    background: #fee2e2;
    color: #991b1b;

    &:hover {
      background: #fecaca;
    }
  }
}

// 空狀態
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  h3 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  p {
    color: #6b7280;
    margin: 0 0 1.5rem 0;
  }
}

// 分頁
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-page {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: #f3f4f6;
    border-color: #3b82f6;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.page-info {
  color: #6b7280;
}

// Modal
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: white;
  border-radius: 0.75rem;
  max-width: 1200px; // 增加寬度以容納左右分欄
  width: 90%;
  max-height: 90vh;
  overflow: visible; // 改為 visible，讓內部的左右面板各自滾動
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;

  h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    margin: 0;
  }
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  transition: color 0.2s;

  &:hover {
    color: #111827;
  }
}

.modal-body {
  padding: 1.5rem;
  flex: 1;
  overflow: visible; // 讓內部元素自行處理滾動
  display: flex;
  flex-direction: column;

  form {
    display: flex;
    flex-direction: column;
    flex: 1;
  }
}

// 建立策略左右分欄佈局
.create-strategy-layout {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.5rem;
  max-height: 70vh; // 限制整體高度

  .left-panel {
    flex: 2; // 左側佔 2/3 寬度
    min-width: 0; // 防止 flex 子元素溢出
    overflow-y: auto; // 左側獨立滾動
    max-height: 70vh; // 設置最大高度
    padding-right: 0.5rem; // 給滾動條留空間

    // 自定義滾動條樣式
    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: #888;
      border-radius: 4px;

      &:hover {
        background: #555;
      }
    }
  }

  .right-panel {
    flex: 1; // 右側佔 1/3 寬度
    min-width: 300px; // 確保右側面板有最小寬度
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    overflow-y: auto; // 右側獨立滾動
    max-height: 70vh; // 設置最大高度
    padding-right: 0.5rem; // 給滾動條留空間

    // 自定義滾動條樣式
    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: #888;
      border-radius: 4px;

      &:hover {
        background: #555;
      }
    }
  }
}

.form-group {
  margin-bottom: 1.5rem;

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #374151;
  }

  input,
  textarea,
  select {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-family: inherit;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }

  textarea {
    resize: vertical;
    font-family: 'Monaco', 'Courier New', monospace;
  }

  select.template-selector {
    background: white;
    cursor: pointer;
    padding-right: 2.5rem;
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
    background-position: right 0.5rem center;
    background-repeat: no-repeat;
    background-size: 1.5em 1.5em;
    appearance: none;

    &:hover {
      border-color: #9ca3af;
    }
  }

  .template-hint {
    margin-top: 0.5rem;
    padding: 0.75rem;
    background: #f0f9ff;
    border-left: 3px solid #3b82f6;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    color: #1e40af;
    line-height: 1.5;
  }

  textarea.code-editor {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
    tab-size: 4;
    background: #f9fafb;

    &:focus {
      background: white;
    }
  }
}

// 引擎類型選擇器
.engine-type-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 0.75rem;
}

.engine-type-btn {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    background: #f9fafb;
  }

  &.active {
    border-color: #3b82f6;
    background: #eff6ff;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);

    .engine-name {
      color: #1e40af;
    }
  }

  .engine-icon {
    font-size: 2rem;
    flex-shrink: 0;
  }

  .engine-info {
    flex: 1;
    text-align: left;
  }

  .engine-name {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 0.25rem;
  }

  .engine-desc {
    font-size: 0.875rem;
    color: #6b7280;
  }
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.template-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
}

.template-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: white;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  .icon {
    font-size: 1rem;
  }

  &:hover {
    background: #f9fafb;
    border-color: #d1d5db;
    color: #374151;
  }

  &.active {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
    box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
  }

  &:active {
    transform: scale(0.98);
  }
}

.factor-templates-container {
  margin-top: 0.75rem;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #e5e7eb;
  }
}

// 編輯器載入狀態
.editor-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  background: #1e1e1e;
  border-radius: 0.5rem;
  min-height: 500px;

  .spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  p {
    color: #9ca3af;
    font-size: 0.875rem;
  }
}

/* 引擎標籤樣式 */
.badges-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.engine-tag {
  font-size: 0.75rem;
  padding: 0.25rem 0.625rem;
  border-radius: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.engine-tag.backtrader {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.engine-tag.qlib {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

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

// 響應式
@media (max-width: 768px) {
      .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .strategies-grid {
    grid-template-columns: 1fr;
  }

  .modal-content {
    width: 95%;
  }

  // 建立策略表單在手機上改為垂直佈局
  .create-strategy-layout {
    flex-direction: column;
    max-height: 80vh; // 手機上給更多高度

    .left-panel,
    .right-panel {
      flex: 1;
      min-width: 0;
      max-height: 50vh; // 手機上每個面板各佔一半
    }
  }
}

// 引擎不匹配警告
.engine-mismatch-warning {
  background: #fffbeb;
  border: 2px solid #fbbf24;
  border-radius: 0.75rem;
  padding: 2rem;
  margin: 1.5rem 0;
  color: #78350f;

  .warning-icon {
    font-size: 3rem;
    text-align: center;
    margin-bottom: 1rem;
  }

  h3 {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: #92400e;
  }

  p {
    font-size: 1rem;
    line-height: 1.6;
    margin-bottom: 1.5rem;
    color: #78350f;
  }

  code {
    background: #fef3c7;
    padding: 0.2rem 0.5rem;
    border-radius: 0.25rem;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.875rem;
    color: #92400e;
    border: 1px solid #fbbf24;
  }

  .options {
    background: white;
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin-top: 1.5rem;
    border: 1px solid #fbbf24;

    h4 {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: #92400e;
    }

    ol {
      list-style: decimal;
      padding-left: 1.5rem;
      margin: 0;

      li {
        margin-bottom: 1.25rem;
        line-height: 1.6;
        color: #78350f;

        &:last-child {
          margin-bottom: 0;
        }

        strong {
          color: #92400e;
          font-weight: 700;
        }

        small {
          display: block;
          margin-top: 0.5rem;
          color: #a16207;
          font-size: 0.875rem;
        }

        ul {
          list-style: disc;
          padding-left: 1.5rem;
          margin-top: 0.75rem;

          li {
            margin-bottom: 0.5rem;
            font-size: 0.875rem;

            code {
              font-size: 0.8125rem;
            }
          }
        }
      }
    }
  }
}
</style>