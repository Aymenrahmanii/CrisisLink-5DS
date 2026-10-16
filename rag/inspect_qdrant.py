"""Quick manual check of what's stored in Qdrant Cloud and whether retrieval works.

Usage:
    python rag/inspect_qdrant.py                      # list collections + counts
    python rag/inspect_qdrant.py structured_index      # dump a few raw points
    python rag/inspect_qdrant.py structured_index "rescue asset for 145 cm water"
                                                        # embed the query and show top-3 hits
"""
import sys
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
QUERY_PREFIX = "query: "  # e5 convention for search queries (index was built with "passage: ")


def main():
    client = QdrantClient(url=os.getenv("qdrant_end_point"), api_key=os.getenv("qdrant"))

    if len(sys.argv) == 1:
        for c in client.get_collections().collections:
            info = client.get_collection(c.name)
            print(f"{c.name}: {info.points_count} points, vector size {info.config.params.vectors.size}")
        return

    collection = sys.argv[1]

    if len(sys.argv) == 2:
        points, _ = client.scroll(collection, limit=5, with_payload=True, with_vectors=False)
        for p in points:
            text = p.payload.get("page_content", "")[:150].replace("\n", " ")
            print(f"[{p.id}] category={p.payload.get('metadata', {}).get('category')}\n  {text}...\n")
        return

    query = sys.argv[2]
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)
    vector = model.encode(QUERY_PREFIX + query).tolist()
    hits = client.query_points(collection, query=vector, limit=3, with_payload=True).points
    for h in hits:
        text = h.payload.get("page_content", "")[:200].replace("\n", " ")
        print(f"score={h.score:.4f} category={h.payload.get('metadata', {}).get('category')}\n  {text}...\n")


if __name__ == "__main__":
    main()
