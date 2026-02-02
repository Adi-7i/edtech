#!/bin/bash

# Simple Task Execution Test
# Prerequisites: Run test_planner.sh first to create a plan

BASE_URL="http://localhost:8000/api/v1"
TODAY=$(date +%Y-%m-%d)

# Use existing test user from planner tests
TEST_EMAIL="planner_test_1770011700@example.com"
TEST_PASSWORD="SecurePass123!"

echo "=============== TASK EXECUTION QUICK TEST ==============="
echo ""

# Login
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\"
  }")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.data.tokens.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed!"
    echo $LOGIN_RESPONSE | jq '.'
    exit 1
fi

echo "✅ Logged in successfully"
echo ""

# Test 1: Get Today's Tasks
echo "1. GET /tasks/today"
curl -s -X GET "$BASE_URL/tasks/today" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
echo ""

# Test 2: Get Tasks for Tomorrow
TOMORROW=$(date -d "+1 day" +%Y-%m-%d 2>/dev/null || date -v+1d +%Y-%m-%d)
echo "2. GET /tasks/date/$TOMORROW"
curl -s -X GET "$BASE_URL/tasks/date/$TOMORROW" \
  -H "Authorization: Bearer $TOKEN" | jq '.data | {date, total_tasks, pending_tasks}'
echo ""

# Test 3: Get Today's Tasks and extract first task ID
echo "3. Getting first task ID from today..."
TODAY_TASKS=$(curl -s -X GET "$BASE_URL/tasks/today" \
  -H "Authorization: Bearer $TOKEN")

TASK_ID=$(echo $TODAY_TASKS | jq -r '.data.tasks[0].id // empty')

if [ -z "$TASK_ID" ]; then
    echo "⚠ No tasks for today. Tests end here."
    echo "Run test_planner.sh first to generate a plan with tasks."
    exit 0
fi

echo "✅ Found task: $TASK_ID"
echo ""

# Test 4: Update Task Time
echo "4. PUT /tasks/$TASK_ID/time (add 30 minutes)"
curl -s -X PUT "$BASE_URL/tasks/$TASK_ID/time" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 30, "mode": "add"}' | jq '.'
echo ""

# Test 5: Update Task Status
echo "5. PUT /tasks/$TASK_ID/status (set to in_progress)"
curl -s -X PUT "$BASE_URL/tasks/$TASK_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress", "notes": "Started working"}' | jq '.'
echo ""

# Test 6: Add more time
echo "6. PUT /tasks/$TASK_ID/time (add 90 more minutes)"
curl -s -X PUT "$BASE_URL/tasks/$TASK_ID/time" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"minutes": 90, "mode": "add"}' | jq '.'
echo ""

# Test 7: Try to mark as completed
echo "7. PUT /tasks/$TASK_ID/status (try to complete)"
curl -s -X PUT "$BASE_URL/tasks/$TASK_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "notes": "Finished!"}' | jq '.'
echo ""

# Test 8: Close the day
echo "8. POST /tasks/day/close (close today)"
curl -s -X POST "$BASE_URL/tasks/day/close" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"date\": \"$TODAY\"}" | jq '.'
echo ""

# Test 9: Try to update after closure (should fail)
echo "9. Try to update task after day is closed (should fail)"
curl -s -X PUT "$BASE_URL/tasks/$TASK_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "pending"}' | jq '.'
echo ""

echo "=============== TESTS COMPLETE ==============="
