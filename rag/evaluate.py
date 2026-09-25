"""Retrieval evaluation: 2 chunking strategies x 2 embedding models on 20 test queries.

Metrics (k = 3, the top-k used by the n8n Qdrant tool):
- Precision@3: share of the top 3 chunks that are relevant
- Hit@3: share of queries with at least one relevant chunk in the top 3
- MRR: mean of 1 / rank of the first relevant chunk (0 if none in the top 10)

Runs fully locally (in-memory Qdrant) so results are reproducible without the cloud cluster.
Writes rag/results/retrieval_eval.md and rag/results/retrieval_eval.json.
"""

import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from chunking import chunk_fixed, chunk_structured, load_corpus, n_tokens

HERE = Path(__file__).resolve().parent
K, MAX_RANK = 3, 10

MODELS = {
    # Current production model (n8n HF Inference node), English-only, 256-token window
    "all-MiniLM-L6-v2": {"id": "sentence-transformers/all-MiniLM-L6-v2", "query": "", "passage": ""},
    # Multilingual candidate (Arabic, French, English), same 384 dimensions, 512-token window
    "multilingual-e5-small": {"id": "intfloat/multilingual-e5-small", "query": "query: ", "passage": "passage: "},
    # What n8n actually sends: the HF Inference node cannot add e5's "query: " prefix to the agent's search text
    "multilingual-e5-small (no query prefix)": {"id": "intfloat/multilingual-e5-small", "query": "", "passage": "passage: "},
}
STRATEGIES = {"fixed": chunk_fixed, "structured": chunk_structured}


def is_relevant(chunk_text: str, relevant: list[list[str]]) -> bool:
    t = chunk_text.lower()
    return any(all(key.lower() in t for key in alt) for alt in relevant)


def main():
    queries = json.loads((HERE / "eval_queries.json").read_text(encoding="utf-8"))["queries"]
    corpus = load_corpus()
    chunks = {name: fn(corpus) for name, fn in STRATEGIES.items()}

    # Can the query be answered at all from ONE chunk of this strategy?
    answerable = {
        s: {q["id"]: any(is_relevant(c["text"], q["relevant"]) for c in cs) for q in queries}
        for s, cs in chunks.items()
    }

    results, per_query = {}, {}
    for model_name, cfg in MODELS.items():
        model = SentenceTransformer(cfg["id"])
        for strat, cs in chunks.items():
            client = QdrantClient(":memory:")
            client.create_collection("eval", vectors_config=VectorParams(size=384, distance=Distance.COSINE))
            vecs = model.encode([cfg["passage"] + c["text"] for c in cs], normalize_embeddings=True)
            client.upsert("eval", [PointStruct(id=i, vector=v.tolist(), payload=c) for i, (c, v) in enumerate(zip(cs, vecs))])

            p_at_k, hits, rr, detail = [], [], [], {}
            for q in queries:
                qv = model.encode(cfg["query"] + q["query"], normalize_embeddings=True).tolist()
                ranked = client.query_points("eval", query=qv, limit=MAX_RANK).points
                rel = [is_relevant(p.payload["text"], q["relevant"]) for p in ranked]
                first = next((i + 1 for i, r in enumerate(rel) if r), None)
                p_at_k.append(sum(rel[:K]) / K)
                hits.append(1.0 if any(rel[:K]) else 0.0)
                rr.append(1 / first if first else 0.0)
                detail[q["id"]] = first
            key = f"{strat} + {model_name}"
            results[key] = {
                "strategy": strat,
                "model": model_name,
                "chunks": len(cs),
                "precision_at_3": round(sum(p_at_k) / len(p_at_k), 3),
                "hit_at_3": round(sum(hits) / len(hits), 3),
                "mrr": round(sum(rr) / len(rr), 3),
                "hit_at_3_en": round(sum(h for h, q in zip(hits, queries) if q["lang"] == "en") / sum(q["lang"] == "en" for q in queries), 3),
                "hit_at_3_fr_ar": round(sum(h for h, q in zip(hits, queries) if q["lang"] != "en") / sum(q["lang"] != "en" for q in queries), 3),
            }
            per_query[key] = detail
            print(f"{key:45s} P@3 {results[key]['precision_at_3']:.3f}  Hit@3 {results[key]['hit_at_3']:.3f}  MRR {results[key]['mrr']:.3f}")

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "retrieval_eval.json").write_text(
        json.dumps({"results": results, "first_relevant_rank": per_query, "answerable": answerable}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = ["# Retrieval Evaluation", "", f"Corpus: `corpus/emergency_protocols.md` ({n_tokens(corpus)} tokens). "
             f"{len(queries)} test queries ({sum(q['lang'] == 'en' for q in queries)} English, "
             f"{sum(q['lang'] == 'fr' for q in queries)} French, {sum(q['lang'] == 'ar' for q in queries)} Tunisian Derja). "
             "A chunk counts as relevant only if it contains every fact of the expected answer.", "",
             "| Chunking | Embedding model | Chunks | Precision@3 | Hit@3 | MRR | Hit@3 EN | Hit@3 FR/AR |",
             "|---|---|---|---|---|---|---|---|"]
    for r in results.values():
        lines.append(f"| {r['strategy']} | {r['model']} | {r['chunks']} | {r['precision_at_3']:.3f} | {r['hit_at_3']:.3f} | {r['mrr']:.3f} | {r['hit_at_3_en']:.3f} | {r['hit_at_3_fr_ar']:.3f} |")
    lines += ["", "## Queries a strategy cannot answer from a single chunk", ""]
    for s, a in answerable.items():
        missing = [qid for qid, ok in a.items() if not ok]
        lines.append(f"- **{s}**: " + (", ".join(missing) if missing else "none"))
    lines += ["", "## Rank of the first relevant chunk per query (- = not in top 10)", "",
              "| Query | " + " | ".join(per_query) + " |", "|---|" + "---|" * len(per_query)]
    for q in queries:
        lines.append(f"| {q['id']} ({q['lang']}) {q['query']} | " + " | ".join(str(per_query[k][q['id']] or '-') for k in per_query) + " |")
    (out / "retrieval_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwritten {out / 'retrieval_eval.md'}")


if __name__ == "__main__":
    main()
