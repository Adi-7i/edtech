#!/bin/bash

# Comprehensive Study Profile Module Test
# Covers: Profile CRUD, Subjects, Chapters

BASE_URL="http://localhost:8000/api/v1"
TIMESTAMP=$(date +%s)
EMAIL="profile_${TIMESTAMP}@test.com"
PASSWORD="TestPassword123!"

echo "=================================================="
echo "Study Profile Module Verification"
echo "USER: $EMAIL"
echo "=================================================="

# 1. Register User
echo ""
echo "[1] Registering User"
REG_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "password": "'"$PASSWORD"'",
    "first_name": "Test",
    "last_name": "User",
    "role": "student"
  }')
echo "$REG_RESPONSE" | python3 -c "import sys, json; print('Status:', json.load(sys.stdin).get('status_code'))"

# 2. Login
echo ""
echo "[2] Logging In"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "'"$EMAIL"'", "password": "'"$PASSWORD"'"}')
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")

if [ -z "$TOKEN" ] || [ "$TOKEN" == "None" ]; then
    echo "Login failed. Exiting."
    exit 1
fi
echo "Login successful. Token acquired."

# 3. Create Profile
echo ""
echo "[3] Creating Study Profile"
CREATE_RESP=$(curl -s -X POST "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "exam_type": "NEET",
    "exam_category": "medical",
    "exam_date": "2026-06-15",
    "daily_study_hours": 6.0,
    "preferences": {
        "learning_style": "visual"
    }
  }')
echo "$CREATE_RESP" | python3 -m json.tool
PROFILE_ID=$(echo "$CREATE_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('id'))")

if [ -z "$PROFILE_ID" ] || [ "$PROFILE_ID" == "None" ]; then
    echo "Profile creation failed. Exiting."
    exit 1
fi

# 4. Get Profile
echo ""
echo "[4] Retrieving Profile"
GET_RESP=$(curl -s -X GET "${BASE_URL}/profile" \
  -H "Authorization: Bearer ${TOKEN}")
echo "$GET_RESP" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Success: {data.get(\"success\")}, Exam: {data.get(\"data\", {}).get(\"exam_type\")}')"

# 5. Update Profile
echo ""
echo "[5] Updating Profile (increasing study hours)"
UPDATE_RESP=$(curl -s -X PUT "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "daily_study_hours": 8.0,
    "exam_type": "NEET UG"
  }')
echo "$UPDATE_RESP" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'New Hours: {data.get(\"data\", {}).get(\"weekly_study_hours\")}')"

# 6. Verify Update
echo ""
echo "[6] Verifying Update"
GET_AGAIN=$(curl -s -X GET "${BASE_URL}/profile" \
  -H "Authorization: Bearer ${TOKEN}")
HOURS=$(echo "$GET_AGAIN" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('daily_study_hours'))")
echo "Updated Daily Hours: $HOURS"

# 7. Get Subjects (should be empty initially)
echo ""
echo "[7] Checking Subjects (Expect Empty)"
SUB_RESP=$(curl -s -X GET "${BASE_URL}/profile/subjects" \
  -H "Authorization: Bearer ${TOKEN}")
echo "$SUB_RESP" | python3 -c "import sys, json; print(f'Total Subjects: {json.load(sys.stdin).get(\"data\", {}).get(\"total\")}')"

echo ""
echo "=================================================="
echo "Verification Complete"
echo "=================================================="
