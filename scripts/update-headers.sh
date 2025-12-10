#!/bin/bash

# 批量更新所有頁面使用 AppHeader 組件

PAGES=(
  "frontend/pages/data/index.vue"
  "frontend/pages/industry/index.vue"
  "frontend/pages/rdagent/index.vue"
  "frontend/pages/strategies/index.vue"
  "frontend/pages/strategies/new.vue"
  "frontend/pages/backtest/index.vue"
  "frontend/pages/backtest/[id].vue"
)

for page in "${PAGES[@]}"; do
  file="/home/ubuntu/QuantLab/$page"

  if [ -f "$file" ]; then
    echo "Processing: $page"

    # 創建備份
    cp "$file" "${file}.bak"

    # 使用 Python 腳本處理文件
    python3 <<EOF
import re

with open('$file', 'r', encoding='utf-8') as f:
    content = f.read()

# 替換 header 部分
header_pattern = r'(<template>\s*<div[^>]*>\s*<!-- 頂部導航欄 -->)\s*<header class="dashboard-header">.*?</header>'

replacement = r'\1\n    <AppHeader />'

# 使用 DOTALL 模式匹配多行
new_content = re.sub(header_pattern, replacement, content, flags=re.DOTALL)

# 如果有變化，寫回文件
if new_content != content:
    with open('$file', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✓ Updated: $page")
else:
    print(f"- No changes needed: $page")
EOF

  else
    echo "✗ File not found: $page"
  fi
done

echo ""
echo "Done! All pages updated."
