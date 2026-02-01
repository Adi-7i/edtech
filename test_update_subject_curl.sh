#!/bin/bash

# Configuration
BASE_URL="http://localhost:8000/api/v1"
MASTER_SUBJECT_ID="697f899a8ce7c30868752e97"  # Physics
TIMESTAMP=$(date +%s)
EMAIL="update_sub_${TIMESTAMP}@example.com"
PASSWORD="TestPassword123!"

echo "=================================================="
echo "Testing Update Subject Feature"
echo "User: $EMAIL"
echo "=================================================="

# 1. Register & Login
echo ""
echo "[1] Auth Setup..."
curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "password": "'"$PASSWORD"'",
    "first_name": "Update",
    "last_name": "Tester",
    "role": "student"
  }' > /dev/null

LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "'"$EMAIL"'", "password": "'"$PASSWORD"'"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")

if [ -z "$TOKEN" ] || [ "$TOKEN" == "None" ]; then
    echo "Login failed!"
    exit 1
fi

# 2. Create Profile
echo ""
echo "[2] Creating Profile..."
curl -s -X POST "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "exam_type": "NEET",
    "exam_category": "medical",
    "exam_date": "2026-06-15",
    "daily_study_hours": 6.0
  }' > /dev/null

# 3. Add Subject
echo ""
echo "[3] Adding Subject..."
ADD_RESP=$(curl -s -X POST "${BASE_URL}/profile/subjects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "subject_ids": ["'"$MASTER_SUBJECT_ID"'"]
  }')

# Extract User Subject ID
USER_SUBJECT_ID=$(echo "$ADD_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])")
echo "Created User Subject ID: $USER_SUBJECT_ID"

if [ -z "$USER_SUBJECT_ID" ] || [ "$USER_SUBJECT_ID" == "None" ]; then
    echo "Failed to get user subject ID"
    exit 1
fi

# 4. Update Subject
echo ""
echo "[4] Updating Subject (Priority=5, Strength=strong)..."
UPDATE_RESP=$(curl -s -X PUT "${BASE_URL}/profile/subjects/${USER_SUBJECT_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "priority": 5,
    "strength": "strong",
    "is_enabled": true
  }')

echo "Response:"
echo "$UPDATE_RESP" | python3 -m json.tool

# 5. Verification
echo ""
echo "[5] Verification..."
PRIORITY=$(echo "$UPDATE_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['priority'])")
STRENGTH=$(echo "$UPDATE_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['strength'])")

echo "Updated Priority: $PRIORITY"
echo "Updated Strength: $STRENGTH"

if [ "$PRIORITY" == "5" ] && [ "$STRENGTH" == "strong" ]; then
    echo "SUCCESS: Subject updated correctly."
else
    echo "FAILURE: Subject update mismatch."
fi

echo ""
echo "=================================================="
echo "Test Complete"
echo "=================================================="
