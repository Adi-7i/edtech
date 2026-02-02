"""
Quick seed script for testing the planner.
Creates sample subjects and chapters.
"""

import asyncio
import os
import sys
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config.settings import settings


async def seed_data():
    """Seed sample subjects and chapters."""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    print("Connected to MongoDB")
    
    # Clear existing data
    await db.subjects.delete_many({})
    await db.chapters.delete_many({})
    print("Cleared existing data")
    
    # Sample exam
    exam_id = ObjectId()
    
    # Create subjects
    subjects_data = [
        {
            "_id": ObjectId(),
            "name": "Physics",
            "code": "PHY",
            "exam_id": exam_id,
            "total_chapters": 3,
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "name": "Chemistry",
            "code": "CHE",
            "exam_id": exam_id,
            "total_chapters": 3,
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "name": "Biology",
            "code": "BIO",
            "exam_id": exam_id,
            "total_chapters": 3,
            "created_at": datetime.utcnow()
        }
    ]
    
    result = await db.subjects.insert_many(subjects_data)
    print(f"Created {len(result.inserted_ids)} subjects")
    
    # Print subject IDs for use in tests
    print("\n=== SUBJECT IDS (use these in tests) ===")
    for subject in subjects_data:
        print(f"{subject['name']}: {subject['_id']}")
    
    # Create chapters for each subject
    chapters_data = []
    for subject in subjects_data:
        for i in range(1, 4):
            chapters_data.append({
                "_id": ObjectId(),
                "subject_id": subject["_id"],
                "name": f"{subject['name']} Chapter {i}",
                "chapter_number": i,
                "topics": [f"Topic {i}.1", f"Topic {i}.2"],
                "created_at": datetime.utcnow()
            })
    
    result = await db.chapters.insert_many(chapters_data)
    print(f"\nCreated {len(result.inserted_ids)} chapters")
    
    # Print first few chapter IDs
    print("\n=== SAMPLE CHAPTER IDS ===")
    for i, chapter in enumerate(chapters_data[:5]):
        print(f"{chapter['name']}: {chapter['_id']}")
    
    print("\n✅ Seeding complete!")
    print(f"\nTo use in test_planner.sh, replace MASTER_SUBJECT_ID with:")
    print(f"  {subjects_data[0]['_id']}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
