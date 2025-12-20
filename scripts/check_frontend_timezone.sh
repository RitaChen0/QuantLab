#!/bin/bash
#
# 前端時區問題檢查工具
#
# 用途：檢查前端 Vue 文件中的時區處理問題
# 使用：bash scripts/check_frontend_timezone.sh
#

echo "=================================="
echo "前端時區問題檢查工具"
echo "=================================="
echo

FRONTEND_DIR="/home/ubuntu/QuantLab/frontend/pages"
ISSUES_FOUND=0
FILES_CHECKED=0

# 檢查 .vue 文件中的 new Date() 使用
check_new_date_usage() {
    local file=$1
    local filename=$(basename "$file")
    local dirname=$(dirname "$file" | sed 's|.*/frontend/pages/||')
    
    # 檢查是否使用 new Date()
    if grep -q "new Date(" "$file"; then
        # 檢查是否已導入 useDateTime 或 useDatePicker
        local has_use_datetime=$(grep -c "useDateTime" "$file" || echo "0")
        local has_use_datepicker=$(grep -c "useDatePicker" "$file" || echo "0")
        
        # 計算 new Date() 的使用次數
        local new_date_count=$(grep -o "new Date(" "$file" | wc -l)
        
        if [ "$has_use_datetime" -eq "0" ] && [ "$has_use_datepicker" -eq "0" ]; then
            echo "❌ $dirname/$filename"
            echo "   ├─ 使用 new Date(): $new_date_count 次"
            echo "   └─ 未導入 useDateTime 或 useDatePicker"
            ((ISSUES_FOUND++))
        else
            echo "⚠️  $dirname/$filename"
            echo "   ├─ 使用 new Date(): $new_date_count 次"
            echo "   └─ 已導入 composables（請手動檢查是否全部替換）"
        fi
        echo
    fi
}

# 遍歷所有 .vue 文件
echo "正在掃描 $FRONTEND_DIR..."
echo

while IFS= read -r -d '' file; do
    ((FILES_CHECKED++))
    check_new_date_usage "$file"
done < <(find "$FRONTEND_DIR" -name "*.vue" -type f -print0 2>/dev/null)

# 總結
echo "=================================="
echo "檢查完成"
echo "=================================="
echo "檢查文件數: $FILES_CHECKED"
echo "發現問題文件數: $ISSUES_FOUND"
echo

if [ "$ISSUES_FOUND" -gt 0 ]; then
    echo "建議："
    echo "1. 查看修復指南: cat /home/ubuntu/QuantLab/FRONTEND_TIMEZONE_FIX_GUIDE.md"
    echo "2. 優先修復核心頁面: data/index.vue, backtest/index.vue"
    echo "3. 使用 useDatePicker 和 useDateTime composables"
    echo
    exit 1
else
    echo "✅ 所有文件都已正確使用時區 composables"
    exit 0
fi
