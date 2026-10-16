"""Index the protocol corpus into Qdrant Cloud with both chunking strategies.

fixed_index      <- Strategy A (recursive splitter, 200 tokens, 40 overlap)
structured_index <- Strategy B (Markdown-structure-aware)   <- used by the n8n Master Triage Agent

Embedding model: intfloat/multilingual-e5-small (384 dims), chosen in rag/results/retrieval_eval.md.
The n8n HF Inference embedding node must use the SAME model, otherwise query and chunk vectors
live in different spaces and retrieval silently returns noise.

Usage: python rag/build_indexes.py   (reads qdrant / qdrant_end_point from .env)
"""

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from chunking import chunk_fixed, chunk_structured, load_corpus

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
PASSAGE_PREFIX = "passage: "  # e5 convention for indexed documents
COLLECTIONS = {"fixed_index": chunk_fixed, "structured_index": chunk_structured}

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def main():
    client = QdrantClient(url=os.getenv("qdrant_end_point"), api_key=os.getenv("qdrant"))
    model = SentenceTransformer(EMBEDDING_MODEL)
    corpus = load_corpus()

    for name, chunker in COLLECTIONS.items():
        chunks = chunker(corpus)
        if client.collection_exists(name):
            client.delete_collection(name)
        client.create_collection(name, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
        # Lets the agent's tools filter by section category (e.g. only hazard_thresholds)
        client.create_payload_index(name, field_name="metadata.category", field_schema=PayloadSchemaType.KEYWORD)

        vectors = model.encode([PASSAGE_PREFIX + c["text"] for c in chunks], normalize_embeddings=True)
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}/{i}")),
                vector=v.tolist(),
                # page_content / metadata is the LangChain layout the n8n Qdrant node reads
                # (its contentPayloadKey is set to page_content)
                payload={"page_content": c["text"], "metadata": {**c["metadata"], "embedding_model": EMBEDDING_MODEL}},
            )
            for i, (c, v) in enumerate(zip(chunks, vectors))
        ]
        client.upsert(name, points)
        print(f"{name}: {len(points)} chunks indexed")


if __name__ == "__main__":
    main()
