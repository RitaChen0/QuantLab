#!/bin/bash
# 測試活躍任務 API

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Testing Active Tasks API...${NC}\n"

# 1. Login to get token
echo -e "${YELLOW}Step 1: Logging in...${NC}"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"locktest2","password":"password123"}' \
  | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo -e "${RED}❌ Login failed${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Login successful${NC}"
echo -e "Token: ${TOKEN:0:20}...\n"

# 2. Get active tasks
echo -e "${YELLOW}Step 2: Querying active tasks...${NC}"
RESPONSE=$(curl -s -X GET http://localhost:8000/api/v1/backtest/tasks/active \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo -e "${GREEN}Response:${NC}"
echo "$RESPONSE" | jq '.'

# 3. Display summary
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Summary:${NC}"
echo "$RESPONSE" | jq -r '.summary | to_entries | .[] | "  \(.key): \(.value)"'
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
