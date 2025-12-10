#!/bin/bash

echo "🔧 QuantLab 開發模式"
echo "=============================="

# 啟動服務
docker-compose up

# 當 Ctrl+C 時停止服務
trap "docker-compose down" EXIT
