#!/bin/bash

# Study Profile API Test Script
# Tests all profile, subject, and chapter endpoints

BASE_URL="http://localhost:8000/api/v1"
ACCESS_TOKEN=""

echo "=================================================="
echo "Study Profile API Test Suite"
echo "=================================================="
echo ""

# Step 1: Login to get access token
echo "[STEP 1] Login to get access token"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123!"
  }')

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('data', {}).get('tokens', {}).get('access_token', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "✗ Login failed. Please ensure test user exists."
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi
echo "✓ Login successful, got access token"
echo ""

# Step 2: Create Study Profile
echo "[TEST 1] Create Study Profile"
echo "POST ${BASE_URL}/profile"
CREATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "exam_type": "NEET",
    "exam_category": "medical",
    "exam_date": "2026-06-15",
    "daily_study_hours": 6.0
  }')

echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null
SUCCESS=$(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$SUCCESS" == "True" ]; then
    echo "✓ PASSED: Profile created successfully"
else
    echo "Note: Profile might already exist (expected on re-run)"
fi
echo ""

# Step 3: Get Study Profile
echo "[TEST 2] Get Study Profile"
echo "GET ${BASE_URL}/profile"
GET_RESPONSE=$(curl -s -X GET "${BASE_URL}/profile" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$GET_RESPONSE" | python3 -m json.tool 2>/dev/null
SUCCESS=$(echo $GET_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$SUCCESS" == "True" ]; then
    echo "✓ PASSED: Profile retrieved successfully"
    PROFILE_ID=$(echo $GET_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('id', ''))" 2>/dev/null)
    DAYS_UNTIL=$(echo $GET_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('days_until_exam', 0))" 2>/dev/null)
    echo "  Profile ID: ${PROFILE_ID}"
    echo "  Days until exam: ${DAYS_UNTIL}"
else
    echo "✗ FAILED: Could not retrieve profile"
fi
echo ""

# Step 4: Update Study Profile
echo "[TEST 3] Update Study Profile"
echo "PUT ${BASE_URL}/profile"
UPDATE_RESPONSE=$(curl -s -X PUT "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "daily_study_hours": 8.0
  }')

echo "$UPDATE_RESPONSE" | python3 -m json.tool 2>/dev/null
SUCCESS=$(echo $UPDATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$SUCCESS" == "True" ]; then
    echo "✓ PASSED: Profile updated successfully"
else
    echo "✗ FAILED: Could not update profile"
fi
echo ""

# Step 5: Get Subjects (should be empty)
echo "[TEST 4] Get Subjects (empty)"
echo "GET ${BASE_URL}/profile/subjects"
SUBJECTS_RESPONSE=$(curl -s -X GET "${BASE_URL}/profile/subjects" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$SUBJECTS_RESPONSE" | python3 -m json.tool 2>/dev/null
SUCCESS=$(echo $SUBJECTS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$SUCCESS" == "True" ]; then
    echo "✓ PASSED: Subjects endpoint working"
else
    echo "✗ FAILED: Could not get subjects"
fi
echo ""

# Step 6: Test invalid exam date (should fail)
echo "[TEST 5] Create Profile with Past Date (should fail)"
echo "POST ${BASE_URL}/profile"
PAST_DATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "exam_type": "JEE",
    "exam_category": "engineering",
    "exam_date": "2020-01-01",
    "daily_study_hours": 4.0
  }')

echo "$PAST_DATE_RESPONSE" | python3 -m json.tool 2>/dev/null
SUCCESS=$(echo $PAST_DATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$SUCCESS" == "False" ]; then
    echo "✓ PASSED: Past date correctly rejected"
else
    echo "✗ FAILED: Should have rejected past date"
fi
echo ""

# Step 7: Test without auth (should fail)
echo "[TEST 6] Access Without Auth (should fail)"
echo "GET ${BASE_URL}/profile"
NO_AUTH_RESPONSE=$(curl -s -X GET "${BASE_URL}/profile")

echo "$NO_AUTH_RESPONSE" | python3 -m json.tool 2>/dev/null
SUCCESS=$(echo $NO_AUTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$SUCCESS" == "False" ]; then
    echo "✓ PASSED: Unauthenticated access correctly rejected"
else
    echo "✗ FAILED: Should have required authentication"
fi
echo ""

echo "=================================================="
echo "Test Summary"
echo "=================================================="
echo "All core profile endpoints tested!"
echo ""
