#!/bin/bash

# Auth Flow End-to-End Test Script
# Tests: guest creation → character creation → claim account → login → token refresh

set -e

API_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================="
echo "Auth Flow E2E Test"
echo "================================="

# 1. Test Guest Creation
echo -e "\n${GREEN}1. Testing Guest Creation...${NC}"
GUEST_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/guest" \
  -H "Content-Type: application/json")

echo "Guest Response: $GUEST_RESPONSE"

GUEST_ACCESS_TOKEN=$(echo $GUEST_RESPONSE | jq -r '.access_token')
GUEST_TOKEN=$(echo $GUEST_RESPONSE | jq -r '.guest_token')
GUEST_USER_ID=$(echo $GUEST_RESPONSE | jq -r '.user.id')
GUEST_USERNAME=$(echo $GUEST_RESPONSE | jq -r '.user.username')

if [ -z "$GUEST_ACCESS_TOKEN" ] || [ "$GUEST_ACCESS_TOKEN" = "null" ]; then
  echo -e "${RED}❌ Failed to create guest account${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Guest created: $GUEST_USERNAME (ID: $GUEST_USER_ID)${NC}"

# 2. Test GET /me with guest token
echo -e "\n${GREEN}2. Testing GET /me with guest token...${NC}"
ME_RESPONSE=$(curl -s -X GET "$API_URL/api/auth/me" \
  -H "Authorization: Bearer $GUEST_ACCESS_TOKEN")

echo "Me Response: $ME_RESPONSE"

ME_USER_ID=$(echo $ME_RESPONSE | jq -r '.id')
if [ "$ME_USER_ID" != "$GUEST_USER_ID" ]; then
  echo -e "${RED}❌ /me returned wrong user${NC}"
  exit 1
fi

echo -e "${GREEN}✓ GET /me works with guest token${NC}"

# 3. Test protected endpoint (create character) with guest token
echo -e "\n${GREEN}3. Testing protected endpoint (create character)...${NC}"
CHARACTER_DATA='{
  "name": "Test Warrior",
  "race": "human",
  "character_class": "fighter",
  "level": 1,
  "strength": 16,
  "dexterity": 14,
  "constitution": 15,
  "intelligence": 10,
  "wisdom": 12,
  "charisma": 8,
  "max_hp": 12,
  "current_hp": 12,
  "backstory": "A brave warrior"
}'

CHARACTER_RESPONSE=$(curl -s -X POST "$API_URL/api/characters" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GUEST_ACCESS_TOKEN" \
  -d "$CHARACTER_DATA")

echo "Character Response: $CHARACTER_RESPONSE"

CHARACTER_ID=$(echo $CHARACTER_RESPONSE | jq -r '.id')
if [ -z "$CHARACTER_ID" ] || [ "$CHARACTER_ID" = "null" ]; then
  echo -e "${RED}❌ Failed to create character with guest token${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Character created: $CHARACTER_ID${NC}"

# 4. Test claim account (upgrade guest to registered)
echo -e "\n${GREEN}4. Testing claim account...${NC}"
CLAIM_EMAIL="test-$(date +%s)@example.com"
CLAIM_PASSWORD="SecurePassword123!"

CLAIM_DATA="{
  \"guest_token\": \"$GUEST_TOKEN\",
  \"email\": \"$CLAIM_EMAIL\",
  \"password\": \"$CLAIM_PASSWORD\"
}"

CLAIM_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/claim-guest" \
  -H "Content-Type: application/json" \
  -d "$CLAIM_DATA")

echo "Claim Response: $CLAIM_RESPONSE"

CLAIM_ACCESS_TOKEN=$(echo $CLAIM_RESPONSE | jq -r '.access_token')
if [ -z "$CLAIM_ACCESS_TOKEN" ] || [ "$CLAIM_ACCESS_TOKEN" = "null" ]; then
  echo -e "${RED}❌ Failed to claim guest account${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Guest account claimed with email: $CLAIM_EMAIL${NC}"

# 5. Test login with claimed account
echo -e "\n${GREEN}5. Testing login with claimed account...${NC}"
LOGIN_DATA="{
  \"email\": \"$CLAIM_EMAIL\",
  \"password\": \"$CLAIM_PASSWORD\"
}"

LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "$LOGIN_DATA")

echo "Login Response: $LOGIN_RESPONSE"

LOGIN_ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
LOGIN_REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')

if [ -z "$LOGIN_ACCESS_TOKEN" ] || [ "$LOGIN_ACCESS_TOKEN" = "null" ]; then
  echo -e "${RED}❌ Failed to login${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}"

# 6. Test GET /me with logged-in token
echo -e "\n${GREEN}6. Testing GET /me with logged-in token...${NC}"
ME_LOGIN_RESPONSE=$(curl -s -X GET "$API_URL/api/auth/me" \
  -H "Authorization: Bearer $LOGIN_ACCESS_TOKEN")

echo "Me Response (logged in): $ME_LOGIN_RESPONSE"

ME_IS_GUEST=$(echo $ME_LOGIN_RESPONSE | jq -r '.is_guest')
if [ "$ME_IS_GUEST" != "false" ]; then
  echo -e "${RED}❌ User should not be guest after claim${NC}"
  exit 1
fi

echo -e "${GREEN}✓ User is no longer guest${NC}"

# 7. Test accessing character created as guest
echo -e "\n${GREEN}7. Testing access to character created as guest...${NC}"
CHARACTER_GET_RESPONSE=$(curl -s -X GET "$API_URL/api/characters/$CHARACTER_ID" \
  -H "Authorization: Bearer $LOGIN_ACCESS_TOKEN")

echo "Character Get Response: $CHARACTER_GET_RESPONSE"

CHARACTER_GET_NAME=$(echo $CHARACTER_GET_RESPONSE | jq -r '.name')
if [ "$CHARACTER_GET_NAME" != "Test Warrior" ]; then
  echo -e "${RED}❌ Failed to access character after claim${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Character accessible after account claim${NC}"

# 8. Test token refresh
echo -e "\n${GREEN}8. Testing token refresh...${NC}"
REFRESH_DATA="{
  \"refresh_token\": \"$LOGIN_REFRESH_TOKEN\"
}"

REFRESH_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "$REFRESH_DATA")

echo "Refresh Response: $REFRESH_RESPONSE"

REFRESHED_ACCESS_TOKEN=$(echo $REFRESH_RESPONSE | jq -r '.access_token')
if [ -z "$REFRESHED_ACCESS_TOKEN" ] || [ "$REFRESHED_ACCESS_TOKEN" = "null" ]; then
  echo -e "${RED}❌ Failed to refresh token${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Token refreshed successfully${NC}"

# 9. Test GET /me with refreshed token
echo -e "\n${GREEN}9. Testing GET /me with refreshed token...${NC}"
ME_REFRESH_RESPONSE=$(curl -s -X GET "$API_URL/api/auth/me" \
  -H "Authorization: Bearer $REFRESHED_ACCESS_TOKEN")

echo "Me Response (refreshed): $ME_REFRESH_RESPONSE"

ME_REFRESH_ID=$(echo $ME_REFRESH_RESPONSE | jq -r '.id')
if [ "$ME_REFRESH_ID" != "$GUEST_USER_ID" ]; then
  echo -e "${RED}❌ Refreshed token returns wrong user${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Refreshed token works${NC}"

# 10. Test unauthorized access (no token)
echo -e "\n${GREEN}10. Testing unauthorized access (no token)...${NC}"
UNAUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/api/characters/$CHARACTER_ID")

HTTP_CODE=$(echo "$UNAUTH_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" != "403" ] && [ "$HTTP_CODE" != "401" ]; then
  echo -e "${RED}❌ Should return 401/403 without token, got $HTTP_CODE${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Protected endpoint blocks unauthorized access${NC}"

# Summary
echo -e "\n================================="
echo -e "${GREEN}✓ All Auth Flow Tests Passed!${NC}"
echo "================================="
echo ""
echo "Summary:"
echo "  - Guest creation: ✓"
echo "  - Guest token works: ✓"
echo "  - Protected endpoints (guest): ✓"
echo "  - Claim account: ✓"
echo "  - Login with claimed account: ✓"
echo "  - Character ownership preserved: ✓"
echo "  - Token refresh: ✓"
echo "  - Unauthorized access blocked: ✓"
echo ""
