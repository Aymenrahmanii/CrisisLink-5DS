import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

# 1. Load keys from your .env file
load_dotenv()

QDRANT_URL = os.getenv("qdrant_end_point")
QDRANT_API_KEY = os.getenv("qdrant")
COLLECTION_NAME = "structured_index"

print(f"Connecting to Qdrant at: {QDRANT_URL}...")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# 2. Embedding model (Matches HuggingFace node in n8n: 384 dimensions)
print("Loading embedding model...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# 3. Create the collection in Qdrant Cloud
client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# 4. Official NOAA / FEMA Flood Protocol Knowledge Chunks
# Tiers follow the Week 1 Milestone Pack: P1 > 100 cm, P2 50-100 cm, P3 20-50 cm, P4 < 20 cm
protocols = [
    {
        "text": "P4 Low / Monitoring - Depth < 20 cm: Pavement flooding, standing or slow-moving water, drainage still working. Negligible structural threat. Cars can navigate with caution. Action: Monitor drainage and issue a public advisory.",
        "depth_cm": 20,
        "priority": "P4",
        "asset": "Patrol Unit / Monitoring Drone",
    },
    {
        "text": "P3 Moderate / Secondary - Depth 20 - 50 cm: Roadway water reaching the bottom of passenger cars and wheel hubs. High stalling hazard, localized property damage. Action: Close low-lying roads, deploy towing assets and barricades.",
        "depth_cm": 50,
        "priority": "P3",
        "asset": "Tow Trucks / Road Closure Barricades",
    },
    {
        "text": "P2 High / Urgent - Depth 50 - 100 cm: Rapidly rising water, vehicles lose traction and can float, stranded motorists. Moving water can knock adults over. Action: Evacuate stranded people with high-clearance 4x4 rescue trucks.",
        "depth_cm": 100,
        "priority": "P2",
        "asset": "High-Clearance 4x4 Tactical Rescue Vehicle",
    },
    {
        "text": "P1 Critical / Immediate - Depth > 100 cm: Structural inundation, submerged vehicles, swift water, extreme danger to human life. Action: Deploy motorized inflatable rescue boats (Zodiac) and request emergency airlift.",
        "depth_cm": 150,
        "priority": "P1",
        "asset": "Inflatable Rescue Boat (Zodiac) / Helicopter Hoist",
    },
    {
        "text": "P1 Critical / Immediate - Vulnerable persons trapped at any depth: elderly people, infants, injured, sick, pregnant or disabled persons who cannot leave a flooded building or vehicle. Action: Dispatch a boat-capable rescue team with a paramedic and prioritize ahead of all P2 incidents.",
        "depth_cm": None,
        "priority": "P1",
        "asset": "Inflatable Rescue Boat (Zodiac) + Paramedic Team",
    },
]

# 5. Index chunks into Qdrant
points = []
for i, item in enumerate(protocols):
    vector = model.encode(item["text"]).tolist()
    points.append(
        PointStruct(
            id=i + 1,
            vector=vector,
            payload={"page_content": item["text"], "metadata": item},
        )
    )

client.upsert(collection_name=COLLECTION_NAME, points=points)
print(
    f" Collection '{COLLECTION_NAME}' successfully created and populated with {len(points)} protocol chunks!"
)