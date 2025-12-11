#!/bin/bash
# Monitor import progress

LOG_FILE="/tmp/top50_import.log"
CHECK_INTERVAL=30  # seconds

echo "🔍 Monitoring TOP 50 import progress..."
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    if [ ! -f "$LOG_FILE" ]; then
        echo "⚠️  Log file not found: $LOG_FILE"
        sleep $CHECK_INTERVAL
        continue
    fi

    # Get log size
    LINES=$(wc -l < "$LOG_FILE")

    # Check for completion marker
    if grep -q "✅ Import Completed" "$LOG_FILE" 2>/dev/null; then
        echo "================================================"
        echo "✅ IMPORT COMPLETED!"
        echo "================================================"
        echo ""

        # Show summary
        tail -30 "$LOG_FILE" | grep -A 20 "Import Completed"

        echo ""
        echo "Full log available at: $LOG_FILE"
        break
    fi

    # Show progress
    TIMESTAMP=$(date +"%H:%M:%S")
    CURRENT_STOCK=$(tail -10 "$LOG_FILE" | grep "stock_id__0" | tail -1 | sed -n "s/.*'stock_id__0': '\([^']*\)'.*/\1/p")

    if [ -n "$CURRENT_STOCK" ]; then
        echo "[$TIMESTAMP] Processing: $CURRENT_STOCK | Log lines: $LINES"
    else
        echo "[$TIMESTAMP] Import in progress... | Log lines: $LINES"
    fi

    sleep $CHECK_INTERVAL
done
