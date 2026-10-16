# CrisisLink-5DS

Citizen-to-Civil-Defense multimodal flood triage. A citizen sends a **photo**, a **voice note** (Tunisian Derja, French or English), a **text** or their **GPS location** to a Telegram bot. A team of AI agents estimates the water depth, extracts who is in danger, retrieves the official flood protocols, grades the incident **P1-P4**, checks the decision with deterministic safety rules, and posts a structured ticket to a dispatcher board and back to the citizen **in their own language** (English, French or Arabic).

Esprit 5DS - Advanced Deep Learning final project.

## Architecture (v3: agents only)

```
Telegram Trigger ──> TRIAGE ORCHESTRATOR (master agent, Gemini 3.8 Flash)
                        ├─ Vision Agent       Qwen 3.8 27B (Gemini fallback)   tool: lookup_reference_height
                        ├─ Distress Agent     gpt-oss-120b                     tools: transcribe_voice (Gemini), transcribe_voice_backup (Whisper),
                        │                                                              convert_level_to_cm, ask_citizen
                        ├─ Protocol Agent     gpt-oss-20b                      tool: Search Flood Protocols (Qdrant + gemini-embedding-001)
                        ├─ Safety Officer     Gemini 3.1 Flash-Lite            tool: check_triage_rules (deterministic code, can only raise priority)
                        ├─ incident memory    load_open_incident, save_incident, close_open_incident, save_chat_location, get_chat_location
                        └─ citizen I/O        send_message, request_location
```

There is no Switch, no IF and no fixed pipeline: the orchestrator reads each message, decides what it is (report, GPS location, `/new`, unsupported content) and which agents to call, in parallel when possible. Specialists answer with schema-validated JSON. Deterministic code lives only inside tools (the safety rules, the reference-height and level tables, Data Table access, Telegram I/O). The previous 53-node pipeline version is kept in `n8n_workflows/legacy_v2_pipeline/` for reference.

## Repository layout

| Path | Contents |
|---|---|
| `n8n_workflows/v3_agentic/` | **The project**: `crisislink_v3_agentic.json` (main workflow) and the two transcription tool workflows; `prompts/` (agent prompts), `check_triage_rules.js` (safety rules), `build_v3.py` (regenerates the JSON files) |
| `n8n_workflows/legacy_v2_pipeline/` | Previous Switch-based pipeline export |
| `corpus/emergency_protocols.md` | RAG knowledge base, 12 sections, 10 cited sources |
| `rag/` | Chunking strategies, Qdrant indexing, retrieval benchmarks (`RETRIEVAL_EVALUATION.md`) |
| `eval/` | Vision and distress-extractor prompt evaluations |
| `prompts/` | Prompt versions and `Prompt_Library.md` (history, techniques, failure log) |
| `docs/` | Technical report (PDF) and presentation (PPTX) |
| `test_media/` | Labelled flood photos and distress voice notes (Derja, French) |
| `start_crisislink.ps1` | Starts the Cloudflare tunnel and n8n with the right webhook URL |

## Install and run

### 1. Accounts and keys

| Service | Used for | Where the key goes |
|---|---|---|
| Telegram @BotFather | Citizen chat bot | n8n credential "Telegram account" |
| Groq | Qwen vision, gpt-oss agents, Whisper backup | n8n credential "Groq account" (Groq type) and "Bearer Auth account" (HTTP Bearer, same key, used by the Whisper tool) |
| Google AI Studio | Gemini agents, Gemini 3.5 Transcribe, Gemini embeddings | n8n credential "Google Gemini(PaLM) Api account" |
| Qdrant Cloud (free cluster) | Vector store | n8n credential "Qdrant account" |

For the Python scripts copy `.env.example` to `.env` and fill in `qdrant`, `qdrant_end_point`, `telegram_bot_token`, `groq_api_key`, `gemini_api_key`, `groq_eval_api_key` (`.env` is git-ignored).

### 2. Knowledge base (once)

```powershell
pip install sentence-transformers qdrant-client python-dotenv requests langchain-text-splitters flask
python rag/build_index_gemini.py     # creates the Qdrant collection structured_index_gemini (used by the workflow)
```

### 3. n8n (2.43 or later)

1. Start n8n: `npx n8n`, or `powershell -ExecutionPolicy Bypass -File .\start_crisislink.ps1`, which also opens a public Cloudflare tunnel so Telegram can reach n8n.
2. **Workflows > Import from file**, in this order:
   1. `n8n_workflows/v3_agentic/crisislink_tool_transcribe_gemini.json`
   2. `n8n_workflows/v3_agentic/crisislink_tool_transcribe_whisper.json`
   3. `n8n_workflows/v3_agentic/crisislink_v3_agentic.json`
   (CLI alternative that keeps the workflow ids: `n8n import:workflow --separate --input=<folder with the three files>`.)
3. Open every node with a credential warning and select your credential (Telegram, Groq, Google Gemini, Bearer Auth, Qdrant). In the two transcription workflows, check the Telegram, Gemini and Bearer Auth nodes too.
4. **Publish both transcription workflows.** n8n refuses to call an unpublished workflow as a tool ("Workflow is not active and cannot be executed").
5. Create two **Data Tables** (they are not part of the export) and select them in the Data Table tools:
   - `crisislink_incidents`: `received_at`, `last_report_at` (date); `report_count`, `depth_cm`, `victim_count`, `latitude`, `longitude` (number); `trapped`, `medical_flag`, `escalate_to_human`, `followup_asked`, `closed` (boolean); and as string: `chat_id`, `input_type`, `priority`, `priority_color`, `depth_confidence`, `rescue_asset`, `guardrail_notes`, `reasoning`, `transcript`, `asr_engine`, `visual_cues`, `photo_file_id`, `vision_json`, `audio_json`, `maps_link`, `location_source`.
   - `crisislink_chat_locations`: `chat_id`; `latitude`, `longitude`, `accuracy_m` (number); `is_live` (boolean); `location_updated_at` (date).
6. In **Search Flood Protocols** check the collection is `structured_index_gemini`, and that **Embeddings (gemini-embedding-001)** is connected to it.
7. **Publish** `CrisisLink v3 - Agentic Triage` (this registers the Telegram webhook; republish whenever the public URL changes; only one workflow can own the bot).

### 4. Use it

Send the bot a photo (a caption is analysed too), a voice note or a text. You get an acknowledgement at once, then the incident ticket in your language; the row appears in `crisislink_incidents`. Tap "Share my location" (Telegram mobile app) to attach GPS. Reports from the same chat within 30 minutes are merged into one incident ("update #2", ...). Send **/new** to close it and start a fresh one, for example between two demo scenarios. Leave about a minute between reports: the free API tiers are rate-limited.

## Evaluations

```powershell
python rag/evaluate.py          # chunking x embedding benchmark (MiniLM, e5)   -> rag/results/retrieval_eval.md
python rag/evaluate_gemini.py   # same benchmark with gemini-embedding-001      -> rag/results/retrieval_eval_gemini.md
python eval/vision_eval.py      # vision prompt V1 vs V2 (29 photos, cached)    -> eval/results/vision_eval.md
python eval/extractor_eval.py   # distress extractor V2 vs V3 vs V4 (8 cases)   -> eval/results/extractor_eval.md
```

Headline results: retrieval Hit@3 0.95 / MRR 0.935 (Gemini embeddings, structure-aware chunks); distress extraction 8/8 cases; vision prompt V2 halves depth under-estimation (55% to 29%) and cuts the error on severe floods from 23 to 5 cm. Details and limits are in `docs/CrisisLink_Technical_Report.pdf`.

## Operating notes

- **Free-tier limits.** Groq allows 8,000 tokens per minute per model; Gemini returns HTTP 429 when busy. Each agent has its own model, and the orchestrator, vision and safety agents have a fallback on the other provider. Run the evaluations with a separate key (`groq_eval_api_key`) so they never use up the demo key's quota.
- **Model retirements.** Providers retire models; every model name is a setting of its chat-model node (list available models with the provider's `/models` endpoint).
- **One editor at a time.** Saving from a stale n8n browser tab overwrites newer changes.
- **Regenerating the workflow files.** `python n8n_workflows/v3_agentic/build_v3.py` rebuilds the three JSON files from the prompt and rules files (it does not touch your n8n instance).
