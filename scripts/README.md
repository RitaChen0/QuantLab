# QuantLab 腳本工具集

> 常用運維和數據管理腳本

---

## 🔄 任務重試工具（NEW!）

### `retry-missed-tasks.sh` ⭐
檢測並重新觸發今天應該執行但被撤銷的定時任務

**快速使用**:
```bash
bash /home/ubuntu/QuantLab/scripts/retry-missed-tasks.sh
```

### `auto-retry-after-restart.sh`
自動監控 backend 容器重啟，並自動執行任務重試

**啟動方式**:
```bash
nohup bash /home/ubuntu/QuantLab/scripts/auto-retry-after-restart.sh > /tmp/auto-retry.log 2>&1 &
```

📖 **詳細文檔**: [TASK_RETRY_GUIDE.md](../TASK_RETRY_GUIDE.md)

---

## 📖 完整文檔

- [TASK_RETRY_GUIDE.md](../TASK_RETRY_GUIDE.md) - 任務重試機制完整指南
- [ADMIN_PANEL_GUIDE.md](../ADMIN_PANEL_GUIDE.md) - 後台管理面板使用指南
- [CLAUDE.md](../CLAUDE.md) - 完整開發指南
