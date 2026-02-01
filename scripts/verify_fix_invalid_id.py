import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "test_subjects@example.com"
TEST_PASSWORD = "Password123!"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("\n=== Verifying Invalid ID Fix ===\n")

        # 1. Login
        print("1. Authenticating...")
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if response.status_code != 200:
            print(f"{RED}Login failed: {response.text}{RESET}")
            # Try registering if not exists (reusing logic from flow script)
            # But assuming user exists from previous run
            return

        token = response.json()["data"]["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"{GREEN}Authenticated.{RESET}")

        # 2. Test Invalid ID
        print("\n2. Sending Invalid Subject ID...")
        invalid_id = "invalid-hex-string"
        response = await client.post(
            f"{BASE_URL}/profile/subjects",
            json={"subject_ids": [invalid_id]},
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 400:
            print(f"{GREEN}PASSED: Server returned 400 Bad Request as expected.{RESET}")
        elif response.status_code == 500:
            print(f"{RED}FAILED: Server returned 500 Internal Server Error (Crash).{RESET}")
        else:
            print(f"{RED}Unexpected Status: {response.status_code}{RESET}")

if __name__ == "__main__":
    asyncio.run(main())
