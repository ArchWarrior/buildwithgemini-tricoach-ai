import datetime
from google.cloud import firestore

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-fde96ef80536"

db = firestore.Client(project=FIRESTORE_PROJECT_ID)
workouts_ref = db.collection("workouts")

SEED_WORKOUTS = [
    {
        "workout_id": "seed-w1",
        "activity_type": "swim",
        "title": "Endurance Pool Sets",
        "duration_minutes": 45.0,
        "distance_miles": 1.5,
        "date": "2026-09-20",
        "perceived_exertion": 6,
        "notes": "Focused on catch technique and consistent pacing across 500m intervals.",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "workout_id": "seed-w2",
        "activity_type": "bike",
        "title": "FTP Threshold Intervals",
        "duration_minutes": 60.0,
        "distance_miles": 18.2,
        "date": "2026-09-21",
        "perceived_exertion": 8,
        "notes": "4x8 min @ 95% FTP on the indoor trainer. High cadence maintained.",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "workout_id": "seed-w3",
        "activity_type": "run",
        "title": "Tempo Brick Run",
        "duration_minutes": 35.0,
        "distance_miles": 4.5,
        "date": "2026-09-22",
        "perceived_exertion": 7,
        "notes": "Off-the-bike transition run. Heavy legs for first 10 minutes, settled into 7:45/mi pace.",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "workout_id": "seed-w4",
        "activity_type": "strength",
        "title": "Core & Leg Stability",
        "duration_minutes": 30.0,
        "distance_miles": 0.0,
        "date": "2026-09-23",
        "perceived_exertion": 5,
        "notes": "Single-leg deadlifts, planks, and hip mobility work.",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
]

def seed():
    print(f"Seeding Firestore collection 'workouts' in project {FIRESTORE_PROJECT_ID}...")
    for item in SEED_WORKOUTS:
        doc_ref = workouts_ref.document(item["workout_id"])
        doc_ref.set(item)
        print(f"  - Seeded {item['activity_type']} workout: '{item['title']}' ({item['date']})")
    print("Done seeding Firestore items!")

if __name__ == "__main__":
    seed()
