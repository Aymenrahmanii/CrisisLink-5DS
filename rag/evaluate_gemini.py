"""Benchmark gemini-embedding-001 on the same 20 queries and both chunking strategies (in-memory, same metrics as evaluate.py).

Usage: python rag/evaluate_gemini.py     (reads gemini_api_key from .env)
Writes rag/results/retrieval_eval_gemini.md
"""
import json
import os
import time
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

from chunking import chunk_fixed, chunk_structured, load_corpus
from evaluate import K, MAX_RANK, is_relevant

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
KEY = os.getenv("gemini_api_key")
MODEL = "gemini-embedding-001"


def embed(texts, task=None):
    """Batch call to the Gemini embedding API. task=None matches what the n8n Gemini embeddings node sends."""
    out = []
    for i in range(0, len(texts), 50):
        reqs = [{"model": "models/" + MODEL, "content": {"parts": [{"text": t}]}, **({"taskType": task} if task else {})} for t in texts[i:i + 50]]
        for attempt in range(6):
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:batchEmbedContents",
                              headers={"x-goog-api-key": KEY}, json={"requests": reqs}, timeout=120)
            if r.status_code == 200:
                break
            time.sleep(10 * (attempt + 1))
        r.raise_for_status()
        out += [e["values"] for e in r.json()["embeddings"]]
    m = np.array(out, dtype="float32")
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def main():
    queries = json.loads((HERE / "eval_queries.json").read_text(encoding="utf-8"))["queries"]
    corpus = load_corpus()
    qv_plain = embed([q["query"] for q in queries])
    rows = []
    for strat, fn in {"fixed": chunk_fixed, "structured": chunk_structured}.items():
        cs = fn(corpus)
        cv = embed([c["text"] for c in cs])
        p_at_k, hits, rr, hits_en, hits_other = [], [], [], [], []
        for q, qv in zip(queries, qv_plain):
            order = np.argsort(-(cv @ qv))[:MAX_RANK]
            rel = [is_relevant(cs[i]["text"], q["relevant"]) for i in order]
            first = next((i + 1 for i, r in enumerate(rel) if r), None)
            p_at_k.append(sum(rel[:K]) / K)
            h = 1.0 if any(rel[:K]) else 0.0
            hits.append(h)
            (hits_en if q["lang"] == "en" else hits_other).append(h)
            rr.append(1 / first if first else 0.0)
        rows.append((strat, len(cs), sum(p_at_k) / len(p_at_k), sum(hits) / len(hits), sum(rr) / len(rr), sum(hits_en) / len(hits_en), sum(hits_other) / len(hits_other)))
        print(f"{strat:11s} {MODEL}: P@3 {rows[-1][2]:.3f} Hit@3 {rows[-1][3]:.3f} MRR {rows[-1][4]:.3f} EN {rows[-1][5]:.2f} FR/AR {rows[-1][6]:.2f}")
    lines = ["# Retrieval evaluation: gemini-embedding-001", "",
             "Same 20 queries and relevance rule as `retrieval_eval.md`; the query is embedded without task type, as the n8n Gemini embeddings node does.", "",
             "| Chunking | Embedding | Chunks | Precision@3 | Hit@3 | MRR | Hit@3 EN | Hit@3 FR/AR |", "|---|---|---|---|---|---|---|---|"]
    for s, n, p, h, m, e, o in rows:
        lines.append(f"| {s} | {MODEL} | {n} | {p:.3f} | {h:.3f} | {m:.3f} | {e:.3f} | {o:.3f} |")
    (HERE / "results" / "retrieval_eval_gemini.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
