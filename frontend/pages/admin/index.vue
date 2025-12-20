<template>
  <div>
    <!-- 頂部導航欄 -->
    <AppHeader />

    <div class="admin-container">
      <!-- Page Header -->
      <div class="admin-header">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">後台管理</h1>
          <p class="text-sm text-gray-500 mt-1">系統管理與監控面板</p>
        </div>
      </div>

    <!-- Tabs -->
    <div class="admin-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['tab-button', activeTab === tab.id ? 'active' : '']"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- Tab Content -->
    <div class="admin-content">
      <!-- System Stats Tab -->
      <div v-show="activeTab === 'stats'" class="tab-pane">
        <h2 class="section-title">系統統計</h2>

        <div v-if="loading.stats" class="loading">載入中...</div>

        <div v-else-if="stats" class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">總用戶數</div>
            <div class="stat-value">{{ stats.total_users }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">活躍用戶</div>
            <div class="stat-value">{{ stats.active_users }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">總策略數</div>
            <div class="stat-value">{{ stats.total_strategies }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">總回測數</div>
            <div class="stat-value">{{ stats.total_backtests }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">資料庫大小</div>
            <div class="stat-value">{{ stats.database_size }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">快取大小</div>
            <div class="stat-value">{{ stats.cache_size }}</div>
          </div>
        </div>

        <!-- Service Health -->
        <h3 class="section-subtitle">服務健康狀態</h3>
        <div v-if="loading.health" class="loading">載入中...</div>
        <div v-else-if="services" class="service-list">
          <div
            v-for="service in services"
            :key="service.service_name"
            class="service-item"
            :class="'status-' + service.status"
          >
            <div class="service-name">{{ service.service_name }}</div>
            <div class="service-status">{{ service.status }}</div>
          </div>
        </div>
      </div>

      <!-- Users Tab -->
      <div v-show="activeTab === 'users'" class="tab-pane">
        <div class="section-header">
          <h2 class="section-title">用戶管理</h2>
          <button @click="loadUsers" class="btn-refresh">🔄 刷新</button>
        </div>

        <div v-if="loading.users" class="loading">載入中...</div>

        <div v-else-if="users.length > 0" class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th @click="toggleSort('id')" class="sortable">
                  ID <span class="sort-icon">{{ getSortIcon('id') }}</span>
                </th>
                <th @click="toggleSort('username')" class="sortable">
                  用戶名 <span class="sort-icon">{{ getSortIcon('username') }}</span>
                </th>
                <th @click="toggleSort('email')" class="sortable">
                  Email <span class="sort-icon">{{ getSortIcon('email') }}</span>
                </th>
                <th @click="toggleSort('full_name')" class="sortable">
                  全名 <span class="sort-icon">{{ getSortIcon('full_name') }}</span>
                </th>
                <th @click="toggleSort('telegram_id')" class="sortable">
                  Telegram ID <span class="sort-icon">{{ getSortIcon('telegram_id') }}</span>
                </th>
                <th @click="toggleSort('telegram_channel_id')" class="sortable">
                  TG 頻道 <span class="sort-icon">{{ getSortIcon('telegram_channel_id') }}</span>
                </th>
                <th @click="toggleSort('member_level')" class="sortable">
                  會員等級 <span class="sort-icon">{{ getSortIcon('member_level') }}</span>
                </th>
                <th @click="toggleSort('cash')" class="sortable">
                  現金 <span class="sort-icon">{{ getSortIcon('cash') }}</span>
                </th>
                <th @click="toggleSort('credit')" class="sortable">
                  信用 <span class="sort-icon">{{ getSortIcon('credit') }}</span>
                </th>
                <th @click="toggleSort('is_active')" class="sortable">
                  狀態 <span class="sort-icon">{{ getSortIcon('is_active') }}</span>
                </th>
                <th @click="toggleSort('is_superuser')" class="sortable">
                  管理員 <span class="sort-icon">{{ getSortIcon('is_superuser') }}</span>
                </th>
                <th @click="toggleSort('created_at')" class="sortable">
                  註冊時間 <span class="sort-icon">{{ getSortIcon('created_at') }}</span>
                </th>
                <th @click="toggleSort('last_login')" class="sortable">
                  最後登入 <span class="sort-icon">{{ getSortIcon('last_login') }}</span>
                </th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in sortedUsers" :key="user.id">
                <td>{{ user.id }}</td>
                <td>{{ user.username }}</td>
                <td>{{ user.email }}</td>
                <td>{{ user.full_name || '-' }}</td>
                <td>{{ user.telegram_id || '-' }}</td>
                <td>{{ user.telegram_channel_id || '-' }}</td>
                <td>
                  <span :class="['level-badge', 'level-' + user.member_level]">
                    Level {{ user.member_level }}
                  </span>
                </td>
                <td class="currency-cell">${{ formatNumber(user.cash) }}</td>
                <td class="currency-cell">{{ formatNumber(user.credit) }}</td>
                <td>
                  <span :class="['status-badge', user.is_active ? 'active' : 'inactive']">
                    {{ user.is_active ? '啟用' : '停用' }}
                  </span>
                </td>
                <td>{{ user.is_superuser ? '是' : '否' }}</td>
                <td>{{ formatDate(user.created_at) }}</td>
                <td>{{ user.last_login ? formatDate(user.last_login) : '-' }}</td>
                <td>
                  <button @click="editUser(user)" class="btn-action">編輯</button>
                  <button @click="deleteUser(user)" class="btn-action btn-danger">刪除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Sync Management Tab -->
      <div v-show="activeTab === 'sync'" class="tab-pane">
        <div class="section-header">
          <h2 class="section-title">數據同步管理</h2>
          <button @click="loadSyncTasks" class="btn-refresh">🔄 刷新</button>
        </div>

        <div v-if="loading.sync" class="loading">載入中...</div>

        <div v-else-if="syncTasks.length > 0" class="sync-tasks">
          <div v-for="task in syncTasks" :key="task.task_name" class="task-card">
            <div class="task-header">
              <h3 class="task-name">{{ task.display_name }}</h3>
              <span :class="['task-status', 'status-' + task.status]">
                {{ task.status }}
              </span>
            </div>
            <div class="task-details">
              <div class="task-info">
                <strong>任務名稱:</strong> {{ task.task_name }}
              </div>
              <div class="task-info">
                <strong>排程:</strong> {{ task.schedule }}
              </div>
              <div class="task-info" v-if="task.last_run">
                <strong>最後執行:</strong> {{ formatDate(task.last_run) }}
                <span
                  v-if="task.last_run_status"
                  :class="['execution-status', 'status-' + task.last_run_status]"
                >
                  {{ getStatusText(task.last_run_status) }}
                </span>
              </div>
              <div class="task-info" v-else>
                <strong>最後執行:</strong> <span class="text-muted">尚未執行</span>
              </div>
              <div class="task-info" v-if="task.last_run_result">
                <strong>執行結果:</strong> {{ task.last_run_result }}
              </div>
              <div class="task-error" v-if="task.error_message">
                <strong>❌ 錯誤訊息:</strong> {{ task.error_message }}
              </div>
            </div>
            <button
              @click="triggerTask(task.task_name)"
              class="btn-trigger"
              :disabled="triggering"
            >
              {{ triggering ? '執行中...' : '立即執行' }}
            </button>
          </div>
        </div>

        <!-- Active Tasks -->
        <h3 class="section-subtitle">執行中的任務</h3>
        <div v-if="activeTasks.length === 0" class="empty-state">
          目前沒有執行中的任務
        </div>
        <div v-else class="task-list">
          <div v-for="task in activeTasks" :key="task.task_id" class="task-item">
            <span class="task-id">{{ task.task_id }}</span>
            <span class="task-name">{{ task.task_name }}</span>
            <span class="task-status">{{ task.status }}</span>
          </div>
        </div>

        <!-- Celery Workers -->
        <h3 class="section-subtitle">Celery Workers</h3>
        <div v-if="workers.length === 0" class="empty-state">
          沒有活躍的 Worker
        </div>
        <div v-else class="worker-list">
          <div v-for="worker in workers" :key="worker.hostname" class="worker-item">
            <div class="worker-name">{{ worker.hostname }}</div>
            <div class="worker-stats">
              <span>狀態: {{ worker.status }}</span>
              <span>⚡ 執行中: {{ worker.current_active }} 個任務</span>
              <span>✅ 累計處理: {{ worker.total_processed }} 個任務</span>
              <span v-if="worker.uptime_seconds">⏱️ 運行時間: {{ formatUptime(worker.uptime_seconds) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Processing Tab -->
      <div v-show="activeTab === 'processing'" class="tab-pane">
        <div class="section-header">
          <h2 class="section-title">數據處理管理</h2>
          <button @click="loadProcessingTasks" class="btn-refresh">🔄 刷新</button>
        </div>

        <div v-if="loading.processing" class="loading">載入中...</div>

        <div v-else-if="processingTasks.length > 0" class="sync-tasks">
          <div v-for="task in processingTasks" :key="task.task_name" class="task-card">
            <div class="task-header">
              <h3 class="task-name">{{ task.display_name }}</h3>
              <span :class="['task-status', 'status-' + task.status]">
                {{ task.status }}
              </span>
            </div>
            <div class="task-details">
              <div class="task-info">
                <strong>任務名稱:</strong> {{ task.task_name }}
              </div>
              <div class="task-info">
                <strong>排程:</strong> {{ task.schedule }}
              </div>
              <div class="task-info" v-if="task.last_run">
                <strong>最後執行:</strong> {{ formatDate(task.last_run) }}
                <span
                  v-if="task.last_run_status"
                  :class="['execution-status', 'status-' + task.last_run_status]"
                >
                  {{ getStatusText(task.last_run_status) }}
                </span>
              </div>
              <div class="task-info" v-else>
                <strong>最後執行:</strong> <span class="text-muted">尚未執行</span>
              </div>
              <div v-if="task.error_message" class="task-info error-message">
                <strong>錯誤:</strong> {{ task.error_message }}
              </div>
            </div>
            <div class="task-actions">
              <button @click="triggerTask(task.task_name)" class="btn-trigger" :disabled="triggering">
                立即執行
              </button>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          沒有數據處理任務
        </div>

        <!-- Description -->
        <div class="info-box">
          <h3>💡 數據處理說明</h3>
          <p><strong>數據處理任務</strong>：從資料庫讀取數據，經過計算或轉換後，存回資料庫或導出文件。</p>
          <ul>
            <li><strong>輸入來源</strong>：PostgreSQL 資料庫</li>
            <li><strong>處理類型</strong>：計算、拼接、清理、轉換</li>
            <li><strong>輸出目標</strong>：資料庫或 Qlib 文件</li>
            <li><strong>特點</strong>：不依賴外部 API，可離線執行，冪等性（可重複執行）</li>
          </ul>
          <p class="mt-2"><strong>範例</strong>：</p>
          <ul>
            <li>生成期貨連續合約：從月份合約拼接為連續合約</li>
            <li>清理過期數據：刪除超過保留期限的舊記錄</li>
            <li>註冊新合約：根據日期計算生成新年度合約</li>
          </ul>
        </div>
      </div>

      <!-- Monitoring Tab -->
      <div v-show="activeTab === 'monitoring'" class="tab-pane">
        <div class="section-header">
          <h2 class="section-title">策略實盤監控</h2>
          <button @click="loadMonitoringTasks" class="btn-refresh">🔄 刷新</button>
        </div>

        <!-- Monitoring Stats -->
        <div v-if="monitoringStats" class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">ACTIVE 策略數</div>
            <div class="stat-value">{{ monitoringStats.active_strategies }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">今日信號</div>
            <div class="stat-value">{{ monitoringStats.signals_today }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">🟢 買入信號</div>
            <div class="stat-value">{{ monitoringStats.buy_signals_today }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">🔴 賣出信號</div>
            <div class="stat-value">{{ monitoringStats.sell_signals_today }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">昨日信號</div>
            <div class="stat-value">{{ monitoringStats.signals_yesterday }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">本週信號</div>
            <div class="stat-value">{{ monitoringStats.signals_week }}</div>
          </div>
        </div>

        <!-- Monitored Stocks -->
        <div v-if="monitoringStats" class="monitored-stocks-section">
          <h3 class="section-subtitle">📈 監控股票清單</h3>
          <div v-if="monitoringStats.monitored_stocks && monitoringStats.monitored_stocks.length > 0" class="stock-chips">
            <span v-for="stock in monitoringStats.monitored_stocks" :key="stock" class="stock-chip">
              {{ stock }}
            </span>
            <span class="stock-count-badge">共 {{ monitoringStats.monitored_stocks.length }} 檔</span>
          </div>
          <div v-else class="empty-state-inline">
            ⚠️ 目前沒有配置任何監控股票
          </div>
        </div>

        <!-- Monitoring Tasks -->
        <h3 class="section-subtitle">監控任務</h3>
        <div v-if="loading.monitoring" class="loading">載入中...</div>
        <div v-else-if="monitoringTasks.length > 0" class="sync-tasks">
          <div v-for="task in monitoringTasks" :key="task.task_name" class="task-card">
            <div class="task-header">
              <h3 class="task-name">{{ task.display_name }}</h3>
              <span :class="['task-status', 'status-' + task.status]">
                {{ task.status }}
              </span>
            </div>
            <div class="task-details">
              <div class="task-info">
                <strong>任務名稱:</strong> {{ task.task_name }}
              </div>
              <div class="task-info">
                <strong>排程:</strong> {{ task.schedule }}
              </div>
              <div class="task-info" v-if="task.last_run">
                <strong>最後執行:</strong> {{ formatDate(task.last_run) }}
                <span
                  v-if="task.last_run_status"
                  :class="['execution-status', 'status-' + task.last_run_status]"
                >
                  {{ getStatusText(task.last_run_status) }}
                </span>
              </div>
              <div class="task-info" v-else>
                <strong>最後執行:</strong> <span class="text-muted">尚未執行</span>
              </div>
              <div class="task-info" v-if="task.last_run_result">
                <strong>執行結果:</strong> {{ task.last_run_result }}
              </div>
              <div class="task-error" v-if="task.error_message">
                <strong>❌ 錯誤訊息:</strong> {{ task.error_message }}
              </div>
            </div>
            <button
              @click="triggerTask(task.task_name)"
              class="btn-trigger"
              :disabled="triggering"
            >
              {{ triggering ? '執行中...' : '立即執行' }}
            </button>
          </div>
        </div>

        <!-- Latest Signals -->
        <h3 class="section-subtitle">最新信號</h3>
        <div v-if="monitoringStats && monitoringStats.latest_signals.length > 0" class="signal-list">
          <div v-for="(signal, index) in monitoringStats.latest_signals" :key="index" class="signal-item">
            <div class="signal-stock">{{ signal.stock_id }}</div>
            <div :class="['signal-type', signal.signal_type === 'BUY' ? 'buy' : 'sell']">
              {{ signal.signal_type === 'BUY' ? '🟢 買入' : '🔴 賣出' }}
            </div>
            <div class="signal-price">NT$ {{ signal.price?.toFixed(2) || 'N/A' }}</div>
            <div class="signal-time">{{ formatDate(signal.detected_at) }}</div>
          </div>
        </div>
        <div v-else class="empty-state">
          目前沒有檢測到任何信號
        </div>

        <!-- Info Box -->
        <div class="info-box">
          <h4>📌 關於策略監控</h4>
          <p>策略監控功能會自動檢測所有 <strong>ACTIVE</strong> 狀態的策略，每 15 分鐘執行一次信號檢測。</p>
          <ul>
            <li>✅ 覆蓋股票交易時段（09:00-13:00）</li>
            <li>✅ 覆蓋期貨夜盤時段（15:00-05:00）</li>
            <li>✅ 自動過濾重複信號（15 分鐘內相同股票相同方向）</li>
            <li>✅ 發送 Telegram 通知給策略擁有者</li>
          </ul>
          <p class="warning">⚠️ <strong>重要</strong>: 策略必須在 parameters 中配置 <code>stocks</code> 陣列，否則不會被監控。</p>
          <p>範例：<code>{"stocks": ["2330", "2317", "2454"]}</code></p>
        </div>
      </div>

      <!-- Logs Tab -->
      <div v-show="activeTab === 'logs'" class="tab-pane">
        <h2 class="section-title">日誌查詢</h2>

        <!-- Log Filters -->
        <div class="log-filters">
          <select v-model="logFilters.level" class="filter-select">
            <option value="">所有級別</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>

          <select v-model="logFilters.module" class="filter-select">
            <option value="">所有模組</option>
            <option value="backend">Backend</option>
            <option value="celery">Celery</option>
            <option value="frontend">Frontend</option>
          </select>

          <input
            v-model="logFilters.keyword"
            type="text"
            placeholder="搜尋關鍵字..."
            class="filter-input"
          />

          <button @click="queryLogs" class="btn-search" :disabled="loading.logs">
            {{ loading.logs ? '查詢中...' : '🔍 查詢' }}
          </button>
        </div>

        <!-- Log Results -->
        <div v-if="loading.logs" class="loading">載入中...</div>
        <div v-else-if="logs.length > 0" class="log-container">
          <div class="log-header">
            共 {{ logs.length }} 筆日誌
          </div>
          <div class="log-list">
            <div
              v-for="(log, index) in logs"
              :key="index"
              :class="['log-entry', 'level-' + log.level.toLowerCase()]"
            >
              <div class="log-meta">
                <span class="log-time">{{ log.timestamp }}</span>
                <span class="log-level">{{ log.level }}</span>
              </div>
              <div class="log-message">{{ log.message }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          請設定篩選條件並點擊查詢
        </div>
      </div>
    </div>

    <!-- Edit User Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>編輯用戶</h2>
          <button @click="closeEditModal" class="btn-close">✕</button>
        </div>

        <div v-if="editError" class="error-message">
          {{ editError }}
        </div>

        <form @submit.prevent="saveUser" class="modal-form">
          <div class="form-group">
            <label>用戶名</label>
            <input v-model="editForm.username" type="text" required>
          </div>

          <div class="form-group">
            <label>Email</label>
            <input v-model="editForm.email" type="email" required>
          </div>

          <div class="form-group">
            <label>全名</label>
            <input v-model="editForm.full_name" type="text">
          </div>

          <div class="form-group">
            <label>Telegram ID</label>
            <input v-model="editForm.telegram_id" type="text" placeholder="@username 或 數字 ID">
            <small class="form-hint">用戶的 Telegram 用戶名或數字 ID</small>
          </div>

          <div class="form-group">
            <label>Telegram 頻道 ID</label>
            <input v-model="editForm.telegram_channel_id" type="text" placeholder="頻道或群組 ID">
            <small class="form-hint">用戶加入的 Telegram 頻道/群組 ID</small>
          </div>

          <div class="form-group">
            <label>會員等級</label>
            <select v-model.number="editForm.member_level" required>
              <option :value="0">Level 0 - 註冊會員</option>
              <option :value="1">Level 1 - 普通會員</option>
              <option :value="2">Level 2 - 中階會員</option>
              <option :value="3">Level 3 - 高階會員</option>
              <option :value="4">Level 4 - VIP會員</option>
              <option :value="5">Level 5 - 系統推廣會員</option>
              <option :value="6">Level 6 - 系統管理員1</option>
              <option :value="7">Level 7 - 系統管理員2</option>
              <option :value="8">Level 8 - 系統管理員3</option>
              <option :value="9">Level 9 - 創造者等級</option>
            </select>
          </div>

          <div class="form-group">
            <label>現金餘額 ($)</label>
            <input v-model.number="editForm.cash" type="number" min="0" step="0.01" placeholder="0.00">
            <small class="form-hint">用戶的現金餘額</small>
          </div>

          <div class="form-group">
            <label>信用點數</label>
            <input v-model.number="editForm.credit" type="number" min="0" step="0.01" placeholder="0.00">
            <small class="form-hint">用戶的信用點數或獎勵積分</small>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="editForm.is_active" type="checkbox">
              <span>啟用帳號</span>
            </label>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="editForm.is_superuser" type="checkbox">
              <span>管理員權限</span>
            </label>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="editForm.email_verified" type="checkbox">
              <span>郵箱已驗證</span>
            </label>
          </div>

          <div class="modal-actions">
            <button type="button" @click="closeEditModal" class="btn-secondary">
              取消
            </button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? '儲存中...' : '儲存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

// 要求管理員權限
definePageMeta({
  middleware: 'admin'
})

const router = useRouter()
const config = useRuntimeConfig()
const { loadUserInfo } = useUserInfo()
const { formatToTaiwanTime } = useDateTime()

// State
const activeTab = ref('stats')

const tabs = [
  { id: 'stats', label: '系統統計', icon: '📊' },
  { id: 'users', label: '用戶管理', icon: '👥' },
  { id: 'sync', label: '數據同步', icon: '🔄' },
  { id: 'processing', label: '數據處理', icon: '⚙️' },
  { id: 'monitoring', label: '策略監控', icon: '🔔' },
  { id: 'logs', label: '日誌查詢', icon: '📝' },
]

const loading = ref({
  stats: false,
  health: false,
  users: false,
  sync: false,
  processing: false,
  monitoring: false,
  logs: false,
})

const stats = ref<any>(null)
const services = ref<any[]>([])
const users = ref<any[]>([])
const syncTasks = ref<any[]>([])
const processingTasks = ref<any[]>([])
const activeTasks = ref<any[]>([])
const workers = ref<any[]>([])
const logs = ref<any[]>([])

// Monitoring state
const monitoringTasks = ref<any[]>([])
const monitoringStats = ref<any>(null)

// Sorting state
const sortBy = ref<string>('id')
const sortOrder = ref<'asc' | 'desc'>('asc')

const triggering = ref(false)

// Computed: Sorted Users
const sortedUsers = computed(() => {
  if (!users.value || users.value.length === 0) return []

  const sorted = [...users.value].sort((a, b) => {
    let aVal = a[sortBy.value]
    let bVal = b[sortBy.value]

    // Handle null/undefined values
    if (aVal == null) aVal = ''
    if (bVal == null) bVal = ''

    // Convert to numbers for numeric fields
    if (['id', 'member_level', 'cash', 'credit'].includes(sortBy.value)) {
      aVal = parseFloat(aVal) || 0
      bVal = parseFloat(bVal) || 0
    }

    // Convert to dates for date fields
    if (['created_at', 'last_login'].includes(sortBy.value)) {
      aVal = aVal ? new Date(aVal).getTime() : 0
      bVal = bVal ? new Date(bVal).getTime() : 0
    }

    // Compare values
    if (aVal < bVal) return sortOrder.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })

  return sorted
})

// Sorting functions
function toggleSort(field: string) {
  if (sortBy.value === field) {
    // Toggle order if clicking the same field
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    // Set new field and default to ascending
    sortBy.value = field
    sortOrder.value = 'asc'
  }
}

function getSortIcon(field: string): string {
  if (sortBy.value !== field) return '⇅'
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

// Edit User Modal State
const showEditModal = ref(false)
const editingUser = ref<any>(null)
const editForm = ref({
  username: '',
  email: '',
  full_name: '',
  telegram_id: '',
  telegram_channel_id: '',
  member_level: 0,
  cash: 0,
  credit: 0,
  is_active: true,
  is_superuser: false,
  email_verified: false,
})
const editError = ref('')
const saving = ref(false)

const logFilters = ref({
  level: '',
  module: '',
  keyword: '',
  limit: 100,
})

// Helper functions
function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (hours > 0) {
    return `${hours} 小時 ${minutes} 分鐘`
  } else {
    return `${minutes} 分鐘`
  }
}

// API calls
async function loadStats() {
  loading.value.stats = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/admin/stats`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    stats.value = response
  } catch (error) {
    console.error('Failed to load stats:', error)
    alert('載入統計資料失敗')
  } finally {
    loading.value.stats = false
  }
}

async function loadHealth() {
  loading.value.health = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch<any[]>(`${config.public.apiBase}/api/v1/admin/health`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    services.value = response
  } catch (error) {
    console.error('Failed to load health:', error)
  } finally {
    loading.value.health = false
  }
}

async function loadUsers() {
  loading.value.users = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch<any[]>(`${config.public.apiBase}/api/v1/admin/users`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    users.value = response
  } catch (error) {
    console.error('Failed to load users:', error)
    alert('載入用戶列表失敗')
  } finally {
    loading.value.users = false
  }
}

async function loadSyncTasks() {
  loading.value.sync = true
  try {
    const token = localStorage.getItem('access_token')

    // Load sync tasks
    const tasks = await $fetch<any[]>(`${config.public.apiBase}/api/v1/admin/sync/tasks`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    syncTasks.value = tasks

    // Load active tasks
    const active = await $fetch<any[]>(`${config.public.apiBase}/api/v1/admin/sync/active-tasks`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    activeTasks.value = active

    // Load workers
    const workerList = await $fetch<any[]>(`${config.public.apiBase}/api/v1/admin/sync/workers`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    workers.value = workerList
  } catch (error) {
    console.error('Failed to load sync tasks:', error)
  } finally {
    loading.value.sync = false
  }
}

async function loadProcessingTasks() {
  loading.value.processing = true
  try {
    const token = localStorage.getItem('access_token')

    // Load processing tasks
    const tasks = await $fetch<any[]>(`${config.public.apiBase}/api/v1/admin/processing/tasks`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    processingTasks.value = tasks
  } catch (error) {
    console.error('Failed to load processing tasks:', error)
  } finally {
    loading.value.processing = false
  }
}

async function loadMonitoringTasks() {
  loading.value.monitoring = true
  try {
    const token = localStorage.getItem('access_token')

    // Load monitoring tasks
    const tasks = await $fetch<any[]>(`${config.public.apiBase}/api/v1/admin/monitoring/tasks`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    monitoringTasks.value = tasks

    // Load monitoring stats
    const stats = await $fetch<any>(`${config.public.apiBase}/api/v1/admin/monitoring/stats`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    monitoringStats.value = stats
  } catch (error) {
    console.error('Failed to load monitoring tasks:', error)
  } finally {
    loading.value.monitoring = false
  }
}

async function triggerTask(taskName: string) {
  if (!confirm(`確定要執行 ${taskName} 嗎？`)) return

  triggering.value = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/admin/sync/trigger`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: { task_name: taskName }
    })

    alert(`任務已提交！\nTask ID: ${response.task_id}`)
    loadSyncTasks()
  } catch (error) {
    console.error('Failed to trigger task:', error)
    alert('執行任務失敗')
  } finally {
    triggering.value = false
  }
}

async function queryLogs() {
  loading.value.logs = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/admin/logs/query`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: logFilters.value
    })

    logs.value = response.logs
  } catch (error) {
    console.error('Failed to query logs:', error)
    alert('查詢日誌失敗')
  } finally {
    loading.value.logs = false
  }
}

// User Management Functions
function editUser(user: any) {
  editingUser.value = user
  editForm.value = {
    username: user.username,
    email: user.email,
    full_name: user.full_name || '',
    telegram_id: user.telegram_id || '',
    telegram_channel_id: user.telegram_channel_id || '',
    member_level: user.member_level || 0,
    cash: parseFloat(user.cash) || 0,
    credit: parseFloat(user.credit) || 0,
    is_active: user.is_active,
    is_superuser: user.is_superuser,
    email_verified: user.email_verified || false,
  }
  editError.value = ''
  showEditModal.value = true
}

function closeEditModal() {
  showEditModal.value = false
  editingUser.value = null
  editError.value = ''
}

async function saveUser() {
  if (!editingUser.value) return

  saving.value = true
  editError.value = ''

  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch(`${config.public.apiBase}/api/v1/admin/users/${editingUser.value.id}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: editForm.value
    })

    // Update user in list
    const index = users.value.findIndex(u => u.id === editingUser.value.id)
    if (index !== -1) {
      users.value[index] = response
    }

    closeEditModal()
    alert('用戶更新成功')
  } catch (error: any) {
    console.error('Failed to update user:', error)
    if (error.data?.detail) {
      editError.value = typeof error.data.detail === 'string'
        ? error.data.detail
        : JSON.stringify(error.data.detail)
    } else {
      editError.value = '更新用戶失敗，請稍後再試'
    }
  } finally {
    saving.value = false
  }
}

async function deleteUser(user: any) {
  // Prevent deleting yourself
  const currentUserId = users.value.find(u => u.is_superuser)?.id
  if (user.id === currentUserId) {
    alert('不能刪除自己的帳號')
    return
  }

  if (!confirm(`確定要刪除用戶 ${user.username} 嗎？\n\n此操作無法復原！`)) {
    return
  }

  try {
    const token = localStorage.getItem('access_token')
    await $fetch(`${config.public.apiBase}/api/v1/admin/users/${user.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    // Remove user from list
    users.value = users.value.filter(u => u.id !== user.id)
    alert(`用戶 ${user.username} 已成功刪除`)
  } catch (error: any) {
    console.error('Failed to delete user:', error)
    if (error.data?.detail) {
      alert('刪除失敗：' + error.data.detail)
    } else {
      alert('刪除用戶失敗，請稍後再試')
    }
  }
}

function formatDate(dateStr: string) {
  return formatToTaiwanTime(dateStr)
}

function getStatusText(status: string) {
  const statusMap: Record<string, string> = {
    'success': '✅ 成功',
    'failed': '❌ 失敗',
    'pending': '⏳ 等待中',
    'running': '▶️ 執行中',
    'unknown': '❓ 未知'
  }
  return statusMap[status] || status
}

function formatNumber(value: any): string {
  const num = parseFloat(value)
  if (isNaN(num)) return '0.00'
  return num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

// Lifecycle
onMounted(() => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    router.push('/login')
    return
  }

  // Load user info for AppHeader
  loadUserInfo()

  // Load initial data
  loadStats()
  loadHealth()
})

// Watch for tab changes and auto-load data
watch(activeTab, (newTab) => {
  if (newTab === 'sync') {
    loadSyncTasks()
  } else if (newTab === 'processing') {
    loadProcessingTasks()
  } else if (newTab === 'monitoring') {
    loadMonitoringTasks()
  } else if (newTab === 'users') {
    loadUsers()
  }
})
</script>

<style scoped lang="scss">
.admin-container {
  min-height: 100vh;
  background: #f9fafb;
  padding-bottom: 2rem;
}

.admin-header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 1.5rem 2rem;
}

.admin-tabs {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  gap: 0.5rem;
  padding: 0 2rem;
}

.tab-button {
  padding: 1rem 1.5rem;
  border: none;
  background: none;
  font-size: 0.9375rem;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;

  &:hover {
    color: #3b82f6;
    background: #f9fafb;
  }

  &.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
    font-weight: 500;
  }
}

.admin-content {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.tab-pane {
  animation: fadeIn 0.3s;
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

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 1.5rem;
}

.section-subtitle {
  font-size: 1.125rem;
  font-weight: 600;
  color: #374151;
  margin: 2rem 0 1rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.btn-refresh, .btn-search {
  padding: 0.5rem 1rem;
  background: #3b82f6;
  color: white;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  transition: all 0.2s;

  &:hover {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

// Stats Grid
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
}

// Service List
.service-list {
  display: grid;
  gap: 1rem;
}

.service-item {
  background: white;
  padding: 1rem 1.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-left: 4px solid;

  &.status-healthy {
    border-left-color: #10b981;
  }

  &.status-unhealthy {
    border-left-color: #ef4444;
  }

  &.status-unknown {
    border-left-color: #f59e0b;
  }
}

.service-name {
  font-weight: 500;
  color: #111827;
}

.service-status {
  font-size: 0.875rem;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-weight: 500;

  .status-healthy & {
    background: #d1fae5;
    color: #065f46;
  }

  .status-unhealthy & {
    background: #fee2e2;
    color: #991b1b;
  }

  .status-unknown & {
    background: #fef3c7;
    color: #92400e;
  }
}

// Table
.table-container {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;

  th, td {
    padding: 0.75rem 1rem;
    text-align: left;
    font-size: 0.875rem;
  }

  thead {
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;

    th {
      font-weight: 600;
      color: #374151;

      &.sortable {
        cursor: pointer;
        user-select: none;
        transition: all 0.2s;

        &:hover {
          background: #f3f4f6;
          color: #111827;
        }

        &:active {
          background: #e5e7eb;
        }
      }
    }
  }

  tbody tr {
    border-bottom: 1px solid #e5e7eb;

    &:hover {
      background: #f9fafb;
    }
  }
}

.sort-icon {
  display: inline-block;
  margin-left: 0.25rem;
  font-size: 0.75rem;
  color: #6b7280;
  opacity: 0.6;
  transition: all 0.2s;

  .sortable:hover & {
    opacity: 1;
    color: #3b82f6;
  }
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;

  &.active {
    background: #d1fae5;
    color: #065f46;
  }

  &.inactive {
    background: #fee2e2;
    color: #991b1b;
  }
}

.level-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  display: inline-block;

  &.level-0 {
    background: #f3f4f6;  // 灰色 - 註冊會員
    color: #6b7280;
  }

  &.level-1 {
    background: #dbeafe;  // 淺藍 - 普通會員
    color: #1e40af;
  }

  &.level-2 {
    background: #d1fae5;  // 綠色 - 中階會員
    color: #065f46;
  }

  &.level-3 {
    background: #fef3c7;  // 金色 - 高階會員
    color: #92400e;
  }

  &.level-4 {
    background: #ffedd5;  // 橙色 - VIP會員
    color: #9a3412;
  }

  &.level-5 {
    background: #fce7f3;  // 粉紅 - 系統推廣會員
    color: #9f1239;
  }

  &.level-6 {
    background: #ede9fe;  // 紫色 - 系統管理員1
    color: #6b21a8;
  }

  &.level-7 {
    background: #e0e7ff;  // 靛色 - 系統管理員2
    color: #3730a3;
  }

  &.level-8 {
    background: #dbeafe;  // 藍色 - 系統管理員3
    color: #1e3a8a;
  }

  &.level-9 {
    background: #fee2e2;  // 紅色 - 創造者等級
    color: #991b1b;
  }
}

.currency-cell {
  font-family: 'Monaco', 'Courier New', monospace;
  font-weight: 600;
  color: #059669;
  text-align: right;
}

.btn-action {
  padding: 0.25rem 0.75rem;
  margin-right: 0.5rem;
  background: #3b82f6;
  color: white;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  transition: all 0.2s;

  &:hover {
    background: #2563eb;
  }

  &.btn-danger {
    background: #ef4444;

    &:hover {
      background: #dc2626;
    }
  }
}

// Sync Tasks
.sync-tasks {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.task-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.task-name {
  font-weight: 600;
  color: #111827;
}

.task-status {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;

  &.status-active {
    background: #d1fae5;
    color: #065f46;
  }
}

.task-details {
  margin-bottom: 1rem;
}

.task-info {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.5rem;

  strong {
    color: #374151;
  }

  .text-muted {
    color: #9ca3af;
    font-style: italic;
  }
}

.task-error {
  font-size: 0.875rem;
  color: #dc2626;
  background: #fee2e2;
  padding: 0.5rem;
  border-radius: 0.25rem;
  margin-top: 0.5rem;
  border-left: 3px solid #ef4444;

  strong {
    color: #991b1b;
  }
}

.execution-status {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 0.5rem;

  &.status-success {
    background: #d1fae5;
    color: #065f46;
  }

  &.status-failed {
    background: #fee2e2;
    color: #991b1b;
  }

  &.status-pending {
    background: #fef3c7;
    color: #92400e;
  }

  &.status-running {
    background: #dbeafe;
    color: #1e40af;
  }

  &.status-unknown {
    background: #f3f4f6;
    color: #6b7280;
  }
}

.btn-trigger {
  width: 100%;
  padding: 0.5rem;
  background: #3b82f6;
  color: white;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

// Task List
.task-list, .worker-list {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 1rem;
}

.task-item, .worker-item {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;

  &:last-child {
    border-bottom: none;
  }
}

.worker-stats {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
}

// Log Filters
.log-filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.filter-select, .filter-input {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.filter-input {
  flex: 1;
  min-width: 200px;
}

// Log Container
.log-container {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.log-header {
  padding: 1rem 1.5rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-weight: 500;
}

.log-list {
  max-height: 600px;
  overflow-y: auto;
}

.log-entry {
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;

  &.level-error {
    background: #fef2f2;
    border-left: 3px solid #ef4444;
  }

  &.level-warning {
    background: #fffbeb;
    border-left: 3px solid #f59e0b;
  }

  &.level-debug {
    color: #6b7280;
  }
}

.log-meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.25rem;
}

.log-time {
  color: #6b7280;
}

.log-level {
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 600;
  font-size: 0.625rem;

  .level-error & {
    background: #ef4444;
    color: white;
  }

  .level-warning & {
    background: #f59e0b;
    color: white;
  }

  .level-info & {
    background: #3b82f6;
    color: white;
  }

  .level-debug & {
    background: #6b7280;
    color: white;
  }
}

.log-message {
  color: #111827;
  white-space: pre-wrap;
  word-break: break-all;
}

// Common
.loading {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: #9ca3af;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

// Modal Styles
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
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;

  h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #111827;
  }
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
    color: #111827;
  }
}

.modal-form {
  padding: 1.5rem;

  .form-group {
    margin-bottom: 1.25rem;

    label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
      color: #374151;
      font-size: 0.875rem;
    }

    input[type="text"],
    input[type="email"],
    input[type="number"],
    select {
      width: 100%;
      padding: 0.625rem;
      border: 1px solid #d1d5db;
      border-radius: 0.5rem;
      font-size: 0.875rem;
      transition: border-color 0.2s;
      background: white;

      &:focus {
        outline: none;
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
      }
    }

    select {
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M10.293 3.293L6 7.586 1.707 3.293A1 1 0 00.293 4.707l5 5a1 1 0 001.414 0l5-5a1 1 0 10-1.414-1.414z'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 0.75rem center;
      padding-right: 2.5rem;
    }

    .form-hint {
      display: block;
      margin-top: 0.375rem;
      font-size: 0.75rem;
      color: #6b7280;
      font-weight: 400;
    }
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    user-select: none;

    input[type="checkbox"] {
      width: 1.125rem;
      height: 1.125rem;
      cursor: pointer;
    }

    span {
      font-weight: 400;
      color: #374151;
    }
  }
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
  margin-top: 0.5rem;

  button {
    padding: 0.625rem 1.25rem;
    border-radius: 0.5rem;
    font-weight: 500;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;

  &:hover:not(:disabled) {
    background: #e5e7eb;
  }
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;

  &:hover:not(:disabled) {
    background: #2563eb;
  }
}

.error-message {
  margin: 0 1.5rem 1rem 1.5rem;
  padding: 0.75rem 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  font-size: 0.875rem;
}

// Monitored Stocks Section
.monitored-stocks-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.stock-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.stock-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.875rem;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
  }
}

.stock-count-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  color: #6b7280;
  border-radius: 9999px;
  font-weight: 500;
  font-size: 0.8125rem;
  border: 1px dashed #d1d5db;
}

.empty-state-inline {
  padding: 1rem;
  color: #f59e0b;
  font-size: 0.9375rem;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 0.375rem;
  text-align: center;
}

// Signal List
.signal-list {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.signal-item {
  display: grid;
  grid-template-columns: 100px 120px 120px 1fr;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  align-items: center;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: #f9fafb;
  }
}

.signal-stock {
  font-weight: 600;
  color: #111827;
  font-size: 1rem;
}

.signal-type {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
  text-align: center;

  &.buy {
    background: #d1fae5;
    color: #065f46;
  }

  &.sell {
    background: #fee2e2;
    color: #991b1b;
  }
}

.signal-price {
  font-family: 'Monaco', 'Courier New', monospace;
  font-weight: 600;
  color: #059669;
  font-size: 0.875rem;
}

.signal-time {
  font-size: 0.875rem;
  color: #6b7280;
}

// Info Box
.info-box {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-top: 2rem;

  h4 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #1e40af;
  }

  p {
    margin: 0.75rem 0;
    font-size: 0.875rem;
    color: #1e40af;
    line-height: 1.6;
  }

  ul {
    margin: 1rem 0;
    padding-left: 1.5rem;

    li {
      margin: 0.5rem 0;
      font-size: 0.875rem;
      color: #1e40af;
    }
  }

  code {
    background: #dbeafe;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.8125rem;
    color: #1e3a8a;
  }

  .warning {
    background: #fef3c7;
    border-left: 3px solid #f59e0b;
    padding: 0.75rem 1rem;
    margin: 1rem 0;
    border-radius: 0.25rem;
    color: #92400e;
  }
}
</style>
