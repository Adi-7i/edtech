#!/bin/bash
# Authentication API Test Script
# Tests all auth endpoints with curl

set -e  # Exit on error

BASE_URL="http://localhost:8000/api/v1"
CONTENT_TYPE="Content-Type: application/json"

echo "=================================================="
echo "Authentication API Test Suite"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Register User
echo -e "${YELLOW}[TEST 1] Register New User${NC}"
echo "POST $BASE_URL/auth/register"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "$CONTENT_TYPE" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User",
    "phone": "+919876543210",
    "role": "student"
  }')

echo "$REGISTER_RESPONSE" | jq '.'
if echo "$REGISTER_RESPONSE" | jq -e '.success == true' > /dev/null; then
  echo -e "${GREEN}✓ PASSED: User registered successfully${NC}\n"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAILED: User registration failed${NC}\n"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

sleep 1

# Test 2: Login User
echo -e "${YELLOW}[TEST 2] Login User${NC}"
echo "POST $BASE_URL/auth/login"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "$CONTENT_TYPE" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!",
    "device_name": "Test Device"
  }')

echo "$LOGIN_RESPONSE" | jq '.'

# Extract tokens
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.tokens.access_token')
REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.tokens.refresh_token')

if [ "$ACCESS_TOKEN" != "null" ] && [ "$ACCESS_TOKEN" != "" ]; then
  echo -e "${GREEN}✓ PASSED: Login successful, tokens received${NC}\n"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAILED: Login failed or no tokens received${NC}\n"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

sleep 1

# Test 3: Get Current User (Protected Route)
echo -e "${YELLOW}[TEST 3] Get Current User Profile (Protected Route)${NC}"
echo "GET $BASE_URL/auth/me"
ME_RESPONSE=$(curl -s -X GET "$BASE_URL/auth/me" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$ME_RESPONSE" | jq '.'

USER_EMAIL=$(echo "$ME_RESPONSE" | jq -r '.data.email')
if [ "$USER_EMAIL" == "testuser@example.com" ]; then
  echo -e "${GREEN}✓ PASSED: Retrieved current user successfully${NC}\n"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAILED: Could not retrieve current user${NC}\n"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

sleep 1

# Test 4: Refresh Access Token
echo -e "${YELLOW}[TEST 4] Refresh Access Token${NC}"
echo "POST $BASE_URL/auth/refresh"
REFRESH_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/refresh" \
  -H "$CONTENT_TYPE" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }")

echo "$REFRESH_RESPONSE" | jq '.'

NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.data.access_token')
if [ "$NEW_ACCESS_TOKEN" != "null" ] && [ "$NEW_ACCESS_TOKEN" != "" ]; then
  echo -e "${GREEN}✓ PASSED: Token refreshed successfully${NC}\n"
  TESTS_PASSED=$((TESTS_PASSED + 1))
  ACCESS_TOKEN="$NEW_ACCESS_TOKEN"  # Update for logout test
else
  echo -e "${RED}✗ FAILED: Token refresh failed${NC}\n"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

sleep 1

# Test 5: Health Check (Unauthenticated)
echo -e "${YELLOW}[TEST 5] Health Check${NC}"
echo "GET $BASE_URL/health"
HEALTH_RESPONSE=$(curl -s -X GET "$BASE_URL/health")

echo "$HEALTH_RESPONSE" | jq '.'

if echo "$HEALTH_RESPONSE" | jq -e '.data.api == "healthy"' > /dev/null; then
  echo -e "${GREEN}✓ PASSED: Health check successful${NC}\n"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAILED: Health check failed${NC}\n"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

sleep 1

# Test 6: Logout
echo -e "${YELLOW}[TEST 6] Logout User${NC}"
echo "POST $BASE_URL/auth/logout"
LOGOUT_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/logout" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }")

echo "$LOGOUT_RESPONSE" | jq '.'

if echo "$LOGOUT_RESPONSE" | jq -e '.success == true' > /dev/null; then
  echo -e "${GREEN}✓ PASSED: Logout successful${NC}\n"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAILED: Logout failed${NC}\n"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

sleep 1

# Test 7: Invalid Token (Should Fail)
echo -e "${YELLOW}[TEST 7] Access with Invalid Token (Should Fail)${NC}"
echo "GET $BASE_URL/auth/me"
INVALID_RESPONSE=$(curl -s -X GET "$BASE_URL/auth/me" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer invalid_token_here")

echo "$INVALID_RESPONSE" | jq '.'

if echo "$INVALID_RESPONSE" | jq -e '.success == false' > /dev/null; then
  echo -e "${GREEN}✓ PASSED: Invalid token correctly rejected${NC}\n"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAILED: Invalid token was accepted${NC}\n"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Summary
echo ""
echo "=================================================="
echo "Test Summary"
echo "=================================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
  echo -e "${GREEN}All tests passed! ✓${NC}"
  exit 0
else
  echo -e "${RED}Some tests failed! ✗${NC}"
  exit 1
fi
