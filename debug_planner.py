#!/usr/bin/env python3
"""Debug planner service directly"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config.settings import settings
from app.modules.planner.service import PlannerService

async def test_preview():
    """Test preview directly"""
    
    # Connect to DB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    # Get user ID from recent test
    user = await db.users.find_one({"email": "planner_test_1770010106@example.com"})
    if not user:
        print("User not found")
        return
    
    user_id = str(user["_id"])
    print(f"Testing with user: {user_id}")
    
    # Test generate
    service = PlannerService(db)
    
    try:
        result = await service.generate_plan(user_id, force_regenerate=True)
        print("\n✅ Generate Success!")
        print(f"Plan ID: {result.plan.id}")
        print(f"Total tasks: {result.plan.total_tasks}")
        print(f"Upcoming days: {len(result.upcoming_days)}")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_preview())
