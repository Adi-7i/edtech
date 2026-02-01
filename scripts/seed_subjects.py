import asyncio
import os
from typing import List, Dict
from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DB_NAME", "smart_study_planner")

# valid object id for exam
NEET_EXAM_ID = ObjectId()
JEE_EXAM_ID = ObjectId()

SUBJECTS = [
    {
        "name": "Physics",
        "code": "PHY",
        "exam_id": NEET_EXAM_ID,
        "total_chapters": 30,
        "is_active": True
    },
    {
        "name": "Chemistry",
        "code": "CHEM",
        "exam_id": NEET_EXAM_ID,
        "total_chapters": 30,
        "is_active": True
    },
    {
        "name": "Biology",
        "code": "BIO",
        "exam_id": NEET_EXAM_ID,
        "total_chapters": 38,
        "is_active": True
    },
    {
        "name": "Mathematics",
        "code": "MATH",
        "exam_id": JEE_EXAM_ID,
        "total_chapters": 25,
        "is_active": True
    }
]

async def seed_subjects():
    print(f"Connecting to MongoDB at {MONGODB_URL}...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    collection = db["subjects"]

    # Clear existing subjects (for development/testing)
    print("Clearing existing subjects...")
    await collection.delete_many({})

    print("Seeding subjects...")
    result = await collection.insert_many(SUBJECTS)
    print(f"Inserted {len(result.inserted_ids)} subjects.")
    
    # Print new IDs
    cursor = collection.find({})
    async for doc in cursor:
        print(f"- {doc['name']} ({doc['code']}): {doc['_id']}")

if __name__ == "__main__":
    asyncio.run(seed_subjects())
