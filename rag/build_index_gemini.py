"""Index the protocol corpus into Qdrant Cloud with gemini-embedding-001 (the index used by the v3 agentic workflow).

structured_index_gemini <- Strategy B (Markdown-structure-aware chunks), 3072-dimensional vectors, cosine.

The n8n "Embeddings Google Gemini" node (model models/gemini-embedding-001) embeds the Protocol Agent's search
query, so indexing and querying use the same model. Benchmark: rag/results/retrieval_eval_gemini.md.

Usage: python rag/build_index_gemini.py   (reads gemini_api_key, qdrant, qdrant_end_point from .env)
"""
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

from chunking import chunk_structured, load_corpus
from evaluate_gemini import MODEL, embed

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
NAME = "structured_index_gemini"


def main():
    client = QdrantClient(url=os.getenv("qdrant_end_point"), api_key=os.getenv("qdrant"))
    chunks = chunk_structured(load_corpus())
    vectors = embed([c["text"] for c in chunks])
    if client.collection_exists(NAME):
        client.delete_collection(NAME)
    client.create_collection(NAME, vectors_config=VectorParams(size=vectors.shape[1], distance=Distance.COSINE))
    client.create_payload_index(NAME, field_name="metadata.category", field_schema=PayloadSchemaType.KEYWORD)
    client.upsert(NAME, [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{NAME}/{i}")),
            vector=v.tolist(),
            # page_content / metadata is the LangChain layout the n8n Qdrant node reads
            payload={"page_content": c["text"], "metadata": {**c["metadata"], "embedding_model": MODEL}},
        )
        for i, (c, v) in enumerate(zip(chunks, vectors))
    ])
    print(f"{NAME}: {len(chunks)} chunks indexed ({vectors.shape[1]} dimensions)")


if __name__ == "__main__":
    main()
