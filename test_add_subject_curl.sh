#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000/api/v1"
SUBJECT_ID="697f899a8ce7c30868752e97"  # Physics from seed output
TIMESTAMP=$(date +%s)
EMAIL="subject_test_${TIMESTAMP}@example.com"
PASSWORD="TestPassword123!"

echo "=================================================="
echo "Testing Add Subject Feature with Curl"
echo "Target Subject ID: $SUBJECT_ID (Physics)"
echo "User: $EMAIL"
echo "=================================================="

# 1. Register User
echo ""
echo "[1] Registering User..."
curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "password": "'"$PASSWORD"'",
    "first_name": "Subject",
    "last_name": "Tester",
    "role": "student"
  }' > /dev/null
echo "User registered."

# 2. Login
echo ""
echo "[2] Logging In..."
LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "'"$EMAIL"'", "password": "'"$PASSWORD"'"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")

if [ -z "$TOKEN" ] || [ "$TOKEN" == "None" ]; then
    echo "Login failed!"
    exit 1
fi
echo "Login successful."

# 3. Create Profile
echo ""
echo "[3] Creating Profile..."
curl -s -X POST "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "exam_type": "NEET",
    "exam_category": "medical",
    "exam_date": "2026-06-15",
    "daily_study_hours": 6.0
  }' > /dev/null
echo "Profile created."

# 4. Add Subject
echo ""
echo "[4] Adding Subject (POST /api/v1/profile/subjects)..."
ADD_RESP=$(curl -s -X POST "${BASE_URL}/profile/subjects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "subject_ids": ["'"$SUBJECT_ID"'"]
  }')

echo "Response:"
echo "$ADD_RESP" | python3 -m json.tool

# 5. Verify Verification
echo ""
echo "[5] Verifying Subject List (GET /api/v1/profile/subjects)..."
GET_RESP=$(curl -s -X GET "${BASE_URL}/profile/subjects" \
  -H "Authorization: Bearer ${TOKEN}")

echo "Response:"
echo "$GET_RESP" | python3 -m json.tool

echo ""
echo "=================================================="
echo "Test Complete"
echo "=================================================="
