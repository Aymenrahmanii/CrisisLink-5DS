# Retrieval evaluation: gemini-embedding-001

Same 20 queries and relevance rule as `retrieval_eval.md`; the query is embedded without task type, as the n8n Gemini embeddings node does.

| Chunking | Embedding | Chunks | Precision@3 | Hit@3 | MRR | Hit@3 EN | Hit@3 FR/AR |
|---|---|---|---|---|---|---|---|
| fixed | gemini-embedding-001 | 23 | 0.400 | 0.950 | 0.818 | 1.000 | 0.800 |
| structured | gemini-embedding-001 | 24 | 0.417 | 0.950 | 0.935 | 1.000 | 0.800 |
