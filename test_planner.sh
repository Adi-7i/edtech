#!/bin/bash

# Smart Study Planner - Planner Module Test Script
# Tests the complete planner workflow from profile creation to plan generation

set -e  # Exit on error

BASE_URL="http://localhost:8000/api/v1"
TIMESTAMP=$(date +%s)
TEST_EMAIL="planner_test_${TIMESTAMP}@example.com"
TEST_PASSWORD="SecurePass123!"

echo "=================================="
echo "STUDY PLANNER ENGINE TEST"
echo "=================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Step 1: Register User
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 1: Register User${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${TEST_EMAIL}\",
    \"password\": \"${TEST_PASSWORD}\",
    \"first_name\": \"Planner\",
    \"last_name\": \"Tester\",
    \"role\": \"student\"
  }")

echo "$REGISTER_RESPONSE" | jq '.'
echo ""

# -----------------------------------------------------------------------------
# Step 2: Login
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 2: Login${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${TEST_EMAIL}\",
    \"password\": \"${TEST_PASSWORD}\",
    \"device_name\": \"Test Script\"
  }")

echo "$LOGIN_RESPONSE" | jq '.'

# Extract access token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.tokens.access_token')
echo -e "${GREEN}✓ Access Token: ${ACCESS_TOKEN:0:20}...${NC}"
echo ""

# -----------------------------------------------------------------------------
# Step 3: Create Study Profile
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 3: Create Study Profile${NC}"
# Set exam date 60 days from now
EXAM_DATE=$(date -d "+60 days" +%Y-%m-%d)

PROFILE_RESPONSE=$(curl -s -X POST "${BASE_URL}/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d "{
    \"exam_type\": \"NEET\",
    \"exam_category\": \"medical\",
    \"exam_date\": \"${EXAM_DATE}\",
    \"daily_study_hours\": 6.0,
    \"preferences\": {
      \"learning_style\": \"visual\",
      \"preferred_language\": \"en\"
    }
  }")

echo "$PROFILE_RESPONSE" | jq '.'
PROFILE_ID=$(echo "$PROFILE_RESPONSE" | jq -r '.data.id')
echo -e "${GREEN}✓ Profile ID: ${PROFILE_ID}${NC}"
echo ""

# -----------------------------------------------------------------------------
# Step 4: Add Subjects
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 4: Add Subjects${NC}"

# Real subject ID from seeded data
MASTER_SUBJECT_ID="698035d8a1a3d82af2c16892"

SUBJECTS_RESPONSE=$(curl -s -X POST "${BASE_URL}/profile/subjects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d "{
    \"subject_ids\": [\"${MASTER_SUBJECT_ID}\"]
  }")

echo "$SUBJECTS_RESPONSE" | jq '.'

# Check if subject was added successfully
if echo "$SUBJECTS_RESPONSE" | jq -e '.success' > /dev/null; then
  USER_SUBJECT_ID=$(echo "$SUBJECTS_RESPONSE" | jq -r '.data[0].id')
  SUBJECT_NAME=$(echo "$SUBJECTS_RESPONSE" | jq -r '.data[0].subject_name')
  echo -e "${GREEN}✓ User Subject ID: ${USER_SUBJECT_ID}${NC}"
  echo -e "${GREEN}✓ Subject Name: ${SUBJECT_NAME}${NC}"
else
  echo -e "${YELLOW}⚠ Could not add subject. Make sure to seed subjects first!${NC}"
  echo -e "${YELLOW}Run: python scripts/seed_subjects.py${NC}"
  USER_SUBJECT_ID=""
fi
echo ""

# -----------------------------------------------------------------------------
# Step 5: Add Chapters (if subject was added)
# -----------------------------------------------------------------------------
if [ -n "$USER_SUBJECT_ID" ]; then
  echo -e "${BLUE}Step 5: Add Chapters${NC}"
  
  # Real chapter IDs from seeded data
  CHAPTERS_RESPONSE=$(curl -s -X POST "${BASE_URL}/profile/subjects/${USER_SUBJECT_ID}/chapters" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -d '{
      "chapter_ids": ["698035d8a1a3d82af2c16895", "698035d8a1a3d82af2c16896", "698035d8a1a3d82af2c16897"]
    }')
  
  echo "$CHAPTERS_RESPONSE" | jq '.'
  
  if echo "$CHAPTERS_RESPONSE" | jq -e '.success' > /dev/null; then
    echo -e "${GREEN}✓ Chapters added${NC}"
    
    # Update chapters with different strengths
    CHAPTER_IDS=($(echo "$CHAPTERS_RESPONSE" | jq -r '.data[].id'))
    
    if [ ${#CHAPTER_IDS[@]} -ge 3 ]; then
      echo -e "${BLUE}Step 5b: Update Chapter Strengths${NC}"
      
      # Set first chapter as weak
      curl -s -X PUT "${BASE_URL}/profile/chapters/${CHAPTER_IDS[0]}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -d '{"strength": "weak"}' | jq '.'
      
      # Set second as medium
      curl -s -X PUT "${BASE_URL}/profile/chapters/${CHAPTER_IDS[1]}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -d '{"strength": "medium"}' | jq '.'
      
      # Set third as strong
      curl -s -X PUT "${BASE_URL}/profile/chapters/${CHAPTER_IDS[2]}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -d '{"strength": "strong"}' | jq '.'
      
      echo -e "${GREEN}✓ Chapter strengths updated${NC}"
    fi
  else
    echo -e "${YELLOW}⚠ Could not add chapters${NC}"
  fi
  echo ""
fi

# -----------------------------------------------------------------------------
# Step 6: Preview Plan
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 6: Preview Study Plan${NC}"
PREVIEW_RESPONSE=$(curl -s -X GET "${BASE_URL}/planner/preview" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$PREVIEW_RESPONSE" | jq '.'

FEASIBILITY=$(echo "$PREVIEW_RESPONSE" | jq -r '.data.feasibility_score')
echo -e "${GREEN}✓ Plan Feasibility: ${FEASIBILITY}${NC}"
echo ""

# -----------------------------------------------------------------------------
# Step 7: Generate Study Plan
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 7: Generate Study Plan${NC}"
GENERATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/planner/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d '{
    "force_regenerate": false,
    "prioritize_weak_only": false,
    "buffer_days": 1
  }')

echo "$GENERATE_RESPONSE" | jq '.'

if echo "$GENERATE_RESPONSE" | jq -e '.success' > /dev/null; then
  PLAN_ID=$(echo "$GENERATE_RESPONSE" | jq -r '.data.plan.id')
  TOTAL_TASKS=$(echo "$GENERATE_RESPONSE" | jq -r '.data.plan.total_tasks')
  echo -e "${GREEN}✓ Plan Generated!${NC}"
  echo -e "${GREEN}  Plan ID: ${PLAN_ID}${NC}"
  echo -e "${GREEN}  Total Tasks: ${TOTAL_TASKS}${NC}"
else
  echo -e "${YELLOW}⚠ Plan generation failed${NC}"
  ERROR=$(echo "$GENERATE_RESPONSE" | jq -r '.message')
  echo -e "${YELLOW}  Error: ${ERROR}${NC}"
fi
echo ""

# -----------------------------------------------------------------------------
# Step 8: Get Active Plan
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 8: Get Active Plan (with upcoming 7 days)${NC}"
ACTIVE_PLAN_RESPONSE=$(curl -s -X GET "${BASE_URL}/planner?days_ahead=7" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$ACTIVE_PLAN_RESPONSE" | jq '.'
echo ""

# -----------------------------------------------------------------------------
# Step 9: Get Daily Plan for Today
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 9: Get Daily Plan for Today${NC}"
TODAY=$(date +%Y-%m-%d)

DAILY_PLAN_RESPONSE=$(curl -s -X GET "${BASE_URL}/planner/daily/${TODAY}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$DAILY_PLAN_RESPONSE" | jq '.'

if echo "$DAILY_PLAN_RESPONSE" | jq -e '.success' > /dev/null; then
  TASK_COUNT=$(echo "$DAILY_PLAN_RESPONSE" | jq -r '.data.task_count')
  TOTAL_HOURS=$(echo "$DAILY_PLAN_RESPONSE" | jq -r '.data.total_allocated_hours')
  echo -e "${GREEN}✓ Daily Plan for ${TODAY}:${NC}"
  echo -e "${GREEN}  Tasks: ${TASK_COUNT}${NC}"
  echo -e "${GREEN}  Total Hours: ${TOTAL_HOURS}${NC}"
else
  echo -e "${YELLOW}⚠ No plan for today yet${NC}"
fi
echo ""

# -----------------------------------------------------------------------------
# Step 10: Get Daily Plan for Tomorrow
# -----------------------------------------------------------------------------
echo -e "${BLUE}Step 10: Get Daily Plan for Tomorrow${NC}"
TOMORROW=$(date -d "+1 day" +%Y-%m-%d)

TOMORROW_PLAN=$(curl -s -X GET "${BASE_URL}/planner/daily/${TOMORROW}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$TOMORROW_PLAN" | jq '.'
echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo "=================================="
echo -e "${GREEN}TEST COMPLETED${NC}"
echo "=================================="
echo ""
echo "Test User: ${TEST_EMAIL}"
echo "Exam Date: ${EXAM_DATE}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Seed subjects: python scripts/seed_subjects.py"
echo "2. Get real subject IDs from database"
echo "3. Re-run this script with valid IDs"
echo ""
echo "To delete the plan and regenerate:"
echo "curl -X DELETE '${BASE_URL}/planner' -H 'Authorization: Bearer ${ACCESS_TOKEN}'"
echo ""
