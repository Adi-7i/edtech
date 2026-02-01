import asyncio
import httpx
import json
import random
import os
from pprint import pprint
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "test_subjects@example.com"
TEST_PASSWORD = "Password123!"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n=== Subject Verification Flow ===\n")

        # 1. Login or Register
        print("1. Authenticating...")
        try:
            # Try login first
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
            )
            
            if response.status_code == 401 or response.status_code == 404:
                # Register if login fails
                print("   Login failed, registering new user...")
                reg_response = await client.post(
                    f"{BASE_URL}/auth/register",
                    json={
                        "email": TEST_EMAIL,
                        "password": TEST_PASSWORD,
                        "first_name": "Subject Tester",
                        "phone": "9876543210"
                    }
                )
                if reg_response.status_code != 201:
                    print(f"{RED}Registration failed: {reg_response.text}{RESET}")
                    # If registration exists but login failed, strictly try login again with json if needed? 
                    # Usually /auth/login is form-data but let's assume standard behavior.
                    return 
                
                # Login again
                response = await client.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
                )

            if response.status_code != 200:
                print(f"{RED}Login failed: {response.text}{RESET}")
                return

            token_data = response.json()
            # Handle different token structures
            if "access_token" in token_data:
                token = token_data["access_token"]
            elif "data" in token_data and "tokens" in token_data["data"]:
                token = token_data["data"]["tokens"]["access_token"]
            else:
                 print(f"{RED}Could not extract token: {token_data}{RESET}")
                 return

            headers = {"Authorization": f"Bearer {token}"}
            print(f"{GREEN}Authenticated successfully.{RESET}")

        except Exception as e:
            print(f"{RED}Auth error: {e}{RESET}")
            return

        # 2. Check/Create Profile
        print("\n2. Checking Study Profile...")
        response = await client.get(f"{BASE_URL}/profile", headers=headers)
        
        if response.status_code == 404:
            print("   Creating new profile...")
            response = await client.post(
                f"{BASE_URL}/profile",
                json={
                    "exam_type": "NEET",
                    "exam_date": "2026-05-01",
                    "daily_study_hours": 6.0
                },
                headers=headers
            )
            if response.status_code != 201:
                print(f"{RED}Failed to create profile: {response.text}{RESET}")
                return
            print(f"{GREEN}Profile created.{RESET}")
        else:
             print(f"{GREEN}Profile exists.{RESET}")

        # 3. Get Master Subjects (Need to know IDs to add)
        # Since we don't have a public endpoint for master subjects in the router we saw,
        # we have to rely on the seed script output or guess.
        # BUT, wait, for the test we need actual IDs.
        # Strategy: We will run the seed script as part of setup or assume known IDs.
        # BETTER: Let's quickly query the DB using a subprocess call to the seed script OR 
        # since we are in python, we can just connect to Mongo directly here too?
        # No, for simplicity, let's assume the user runs the seed script first and we can query via a helper
        # or we scan the 'subjects' collection directly if we could.
        # But this script runs "externally".
        
        # Let's use a small mongo connection helper here just to get IDs for the test
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_client = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
        db = mongo_client[os.getenv("MONGODB_DB_NAME", "smart_study_planner")]
        master_subjects = await db.subjects.find().to_list(length=10)
        
        if not master_subjects:
            print(f"{RED}No master subjects found in DB. Please run seed_subjects.py first.{RESET}")
            return
        
        print(f"Found {len(master_subjects)} master subjects.")
        target_subject = master_subjects[0]
        target_subject_id = str(target_subject["_id"])
        print(f"Target Subject: {target_subject['name']} ({target_subject_id})")

        # 4. Add Subject
        print(f"\n3. Adding Subject: {target_subject['name']}...")
        response = await client.post(
            f"{BASE_URL}/profile/subjects",
            json={"subject_ids": [target_subject_id]},
            headers=headers
        )
        
        if response.status_code == 201:
            print(f"{GREEN}Subject added successfully.{RESET}")
            data = response.json().get("data", [])
            if not data:
                print(f"{RED}Unexpected empty data response.{RESET}")
            else:
                 user_subject_id = data[0]["id"]
                 print(f"User Subject ID: {user_subject_id}")
        elif response.status_code == 200: 
             # Maybe it returns 200 if already exists? Router said 201.
             print(f"{GREEN}Request successful (maybe already added).{RESET}")
             # Need to find the ID though
             subjects_resp = await client.get(f"{BASE_URL}/profile/subjects", headers=headers)
             subjects = subjects_resp.json().get("data", {}).get("subjects", [])
             found = next((s for s in subjects if s["subject_id"] == target_subject_id), None)
             if found:
                 user_subject_id = found["id"]
                 print(f"Found existing User Subject ID: {user_subject_id}")
             else:
                 print(f"{RED}Could not verify subject addition.{RESET}")
                 return
        else:
            print(f"{RED}Failed to add subject: {response.text}{RESET}")
            # Continue to see if we can get list
            # return

        # 5. Get Subjects
        print("\n4. Getting Subjects...")
        response = await client.get(f"{BASE_URL}/profile/subjects", headers=headers)
        if response.status_code == 200:
            data = response.json()["data"]
            subjects = data["subjects"]
            print(f"{GREEN}Retrieved {len(subjects)} subjects.{RESET}")
            if len(subjects) > 0:
                print(f"First subject: {subjects[0]['subject_name']} (Enabled: {subjects[0]['is_enabled']})")
                user_subject_id = subjects[0]["id"] # Update ID to be sure
            else:
                print(f"{RED}Subject list is empty!{RESET}")
                return
        else:
            print(f"{RED}Failed to get subjects: {response.text}{RESET}")
            return

        # 6. Update Subject
        print(f"\n5. Updating Subject {user_subject_id} (Disable)...")
        response = await client.put(
            f"{BASE_URL}/profile/subjects/{user_subject_id}",
            json={"is_enabled": False, "priority": 2},
            headers=headers
        )
        
        if response.status_code == 200:
            updated = response.json()["data"]
            print(f"{GREEN}Update successful.{RESET}")
            print(f"New Status - Enabled: {updated['is_enabled']}, Priority: {updated['priority']}")
            
            if updated['is_enabled'] is False and updated['priority'] == 2:
                 print(f"{GREEN}Verification: Update persisted correctly.{RESET}")
            else:
                 print(f"{RED}Verification: Update fields mismatch!{RESET}")
        else:
             print(f"{RED}Failed to update subject: {response.text}{RESET}")

        # 7. Final Verification (Read back)
        print("\n6. Final Verification (Get Subjects)...")
        response = await client.get(f"{BASE_URL}/profile/subjects", headers=headers)
        subjects = response.json()["data"]["subjects"]
        target = next((s for s in subjects if s["id"] == user_subject_id), None)
        if target:
            print(f"Final State: {target['subject_name']} - Enabled: {target['is_enabled']}")
            if not target['is_enabled']:
                 print(f"{GREEN}PASSED: Subject flow verification complete.{RESET}")
            else:
                 print(f"{RED}FAILED: Subject should be disabled.{RESET}")
        else:
            print(f"{RED}FAILED: Subject not found in list.{RESET}")

if __name__ == "__main__":
    asyncio.run(main())
