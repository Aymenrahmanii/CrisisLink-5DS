# Retrieval Evaluation - CrisisLink

Deliverable 4. Raw results and per-query ranks: `rag/results/retrieval_eval.md`. Reproduce with `python rag/evaluate.py`.

## Setup

- **Corpus**: `corpus/emergency_protocols.md`, 12 sections, 3,357 tokens, 10 cited sources (NWS, FEMA, AIDR Guideline 7-3, CDC, Tunisian Civil Protection, Jaslow et al. 2019, plus the team's priority and asset tables). Several sections are tables whose rows only make sense together with their header (tier, depth, asset).
- **Test set**: 20 queries (15 English, 3 French, 2 Tunisian Derja), `rag/eval_queries.json`. A chunk counts as relevant only if it contains **every** fact of the expected answer (for example "P2" **and** "High-Clearance 4x4"), so a chunk that separates a table row from its meaning does not count.
- **Strategies**: A = recursive splitter, 200 tokens, 40 overlap. B = Markdown-structure-aware: one chunk per section, tables never cut inside a row, header repeated when a table is split, heading path prefixed to every chunk.
- **Embedding models**: `all-MiniLM-L6-v2` (English, previous production model) and `multilingual-e5-small` (Arabic/French/English), both 384 dimensions; Qdrant, cosine similarity, top-k = 3 (the value used by the n8n tool).

## Results

| Chunking | Embedding | Precision@3 | Hit@3 | MRR | Hit@3 English | Hit@3 French/Derja |
|---|---|---|---|---|---|---|
| A fixed | MiniLM | 0.300 | 0.80 | 0.706 | 0.93 | 0.40 |
| B structured | MiniLM | 0.300 | 0.75 | 0.699 | 0.93 | 0.20 |
| A fixed | e5-small | 0.367 | 0.85 | 0.780 | 0.93 | 0.60 |
| **B structured** | **e5-small** | **0.383** | **0.90** | **0.818** | **1.00** | **0.60** |
| B structured | e5-small, no query prefix (what n8n sends) | 0.383 | 0.90 | 0.817 | 1.00 | 0.60 |

## Comments

1. **Precision@3 looks low, but its ceiling is 0.47.** Most queries have exactly one relevant chunk in the corpus, so a perfect retriever scores 1/3 on them. The best achievable Precision@3 is 0.467 for strategy B and 0.483 for A; B + e5 reaches 0.383, i.e. 82% of its ceiling. Hit@3 and MRR are the more informative metrics here.
2. **The embedding model mattered more than the chunking.** With MiniLM, structure-aware chunking was *not* better (Hit@3 0.75 vs 0.80). With e5, it became the best configuration (0.90, MRR 0.818). We report this rather than claiming structure-aware chunking wins everywhere.
3. **Multilingual queries were the main weakness of MiniLM**: at most 2 of the 5 French/Derja queries are answered in the top 3, and two of them (q18 in French, q20 in Derja) are not found even in the top 10. e5 answers 3 of 5 in the top 3 and finds all 5 in the top 10. Citizens write in Derja and French, but in production the agent writes its search query in English, so the English score (1.00 with B + e5) is the one that matters most live.
4. **Table integrity.** At this corpus size, 200-token fixed chunks rarely cut a table row, so no query became unanswerable (both strategies can answer all 20 from a single chunk). The benefit of B shows in ranking: the hazard-class query (q05, needs class + description + depth limit together) ranks 2nd with B + e5 against 4th with A + e5 and 9th with A + MiniLM. The playbook expected "Strategy A cuts the tables in half"; on our corpus the effect was weaker than expected.
5. **Why 200 tokens and not 300 for strategy A**: MiniLM truncates input after 256 tokens, so 300-token chunks would be silently cut before embedding. B's maximum chunk is 240 tokens for the same reason.
6. **Production end-to-end check.** In n8n, the query from failed execution #49 ("rescue asset for 145 cm floodwater with submerged car") now returns the complete rescue-asset table first (score 0.86), where the old 5-sentence index returned the P2 chunk and led to the wrong asset.

## Update: production embedding model is now gemini-embedding-001

The Hugging Face Inference API used by the first version ran out of free credits, so the v3 workflow embeds queries with Google's `gemini-embedding-001` through the native n8n Gemini embeddings node (same Google credential as the LLMs, no extra service). Because queries and chunks must use the same model, the structure-aware chunks were re-indexed into the Qdrant collection `structured_index_gemini` (`python rag/build_index_gemini.py`) and the benchmark was re-run on the same 20 queries with the same relevance rule (`python rag/evaluate_gemini.py`, raw table in `rag/results/retrieval_eval_gemini.md`).

| Chunking | Embedding | Precision@3 | Hit@3 | MRR | Hit@3 EN | Hit@3 FR/Derja |
|---|---|---|---|---|---|---|
| B structured | multilingual-e5-small (previous production) | 0.383 | 0.90 | 0.818 | 1.00 | 0.60 |
| A fixed | gemini-embedding-001 | 0.400 | 0.95 | 0.818 | 1.00 | 0.80 |
| **B structured** | **gemini-embedding-001 (production)** | **0.417** | **0.95** | **0.935** | **1.00** | **0.80** |

Structure-aware chunking keeps its advantage in ranking with the new model (MRR 0.935 vs 0.818 for fixed windows). The e5 results above remain the reference for the chunking x embedding comparison and the `structured_index` collection is kept. Caveat: vectors have 3,072 dimensions and Gemini's free tier rate-limits (HTTP 429) when other Gemini agents are busy.

## What did not work

- **Metadata filtering.** Every chunk carries a `category` (priority_matrix, hazard_thresholds, rescue_assets, ...) and Qdrant has a payload index on it. We planned two filtered tools (thresholds vs procedures), but the n8n Qdrant node (v1.3) ignored `searchFilterJson` in both syntaxes we tried (test executions #60 and #61 returned out-of-category chunks). Production therefore uses one unfiltered tool; the categories remain for future use.
- **No reranker**: with 24 chunks and top-3, a reranker would add latency and a paid API for little gain; revisit if the corpus grows.

## Limitations

- 20 queries written by the team (risk of vocabulary overlap with the corpus); relevance is judged by exact fact strings, which is strict and objective but can miss paraphrased answers.
- The corpus is small (3.4k tokens) by design: it holds the official thresholds and procedures the triage agent needs, not a general flood encyclopedia. A larger corpus would make chunking differences more visible.
