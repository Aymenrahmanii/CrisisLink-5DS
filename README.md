# CrisisLink-5DS

Citizen-to-Civil-Defense multimodal flood triage. A citizen sends a **photo**, a **voice note** (Tunisian Derja, French or English), a **text** or their **GPS location** to a Telegram bot. An n8n pipeline of specialist agents estimates the water depth, extracts who is in danger, retrieves the official flood protocols, grades the incident P1-P4, enforces safety guardrails, and posts a structured ticket to a dispatcher board and back to the citizen.

Esprit 5DS - Advanced Deep Learning final project.

## Architecture

```
Telegram ──> Normalize Input ──> "report received" ──> Route by Media (deterministic router)
   ├─ photo ──> VISION AGENT (Qwen 3.8 27B, Gemini Flash-Lite fallback)
   │              tool: lookup_reference_height          (+ photo caption ──> Distress Agent)
   ├─ voice ──> Gemini 3.5 Transcribe ─(fails)─> Whisper large-v3 ──┐
   ├─ text  ────────────────────────────────────────────────────────┴──> DISTRESS AGENT (gpt-oss-120b)
   │                                                     tools: convert_level_to_cm, ask_citizen (1 follow-up question)
   ├─ GPS   ──> save location, attach to open incidents
   ├─ /new  ──> close the open incident
   └─ other ──> "please send a photo / voice / text"
Vision JSON / Distress JSON ──> Incident Fusion (same chat, < 30 min = one incident)
    ──> MASTER TRIAGE AGENT (gpt-oss-120b, tool: Search Flood Protocols = RAG on Qdrant)
    ──> Safety Guardrail (deterministic rules) ──> attach GPS
    ──> Dispatcher board (n8n Data Table, upsert) ──> Telegram ticket (+ "share location" button)
```

Three agents, each with its own model and tools: two specialist workers (Vision, Distress) and the Master Triage orchestrator. Routing and transcription stay deterministic on purpose: every photo must be analysed, and n8n cannot pass images through agent-to-agent tool calls.

## Repository layout

| Path | Contents |
|---|---|
| `n8n_workflows/crisislink_workflow.json` | Exported n8n workflow (import this) |
| `corpus/emergency_protocols.md` | RAG knowledge base, 12 sections, 10 cited sources |
| `rag/` | Chunking strategies, Qdrant indexing, retrieval evaluation |
| `eval/` | Vision and extractor prompt evaluations |
| `prompts/` | Prompt versions and `Prompt_Library.md` |
| `test_media/` | Labelled flood photos and distress voice notes |
| `start_crisislink.ps1` | Starts the tunnel + n8n and re-links Claude Code |

## Setup

### 1. Accounts and keys

| Service | Used for | Where the key goes |
|---|---|---|
| Telegram @BotFather | Citizen chat bot | n8n credential "Telegram account" |
| Groq | Vision (Qwen), Whisper, extractor and agent (gpt-oss-120b) | n8n credentials "Groq account" (Groq type) and "Bearer Auth account" (HTTP Bearer) |
| Google AI Studio | Gemini 3.5 Transcribe | n8n credential of type "Google Gemini (PaLM) API" |
| Qdrant Cloud (free cluster) | Vector store | n8n credential "Qdrant account" |
| Hugging Face | Query embeddings (multilingual-e5-small) | n8n credential "Hugging Face account" |

For the Python scripts, copy `.env.example` to `.env` and fill in the same keys (`.env` is git-ignored).

### 2. Python (knowledge base and evaluations)

```powershell
pip install sentence-transformers qdrant-client python-dotenv requests langchain-text-splitters
python rag/build_indexes.py      # creates fixed_index and structured_index in Qdrant Cloud
```

### 3. n8n

1. Start n8n (`npx n8n`, or run `start_crisislink.ps1`, which also opens a public Cloudflare tunnel so Telegram can reach n8n).
2. **Workflows > Import from file** > `n8n_workflows/crisislink_workflow.json`.
3. Open each node with a credential warning and select your credential (Telegram, Groq, Bearer Auth, Google Gemini, Qdrant, Hugging Face).
4. Create two **Data Tables** (they are not part of the workflow export) and select them in the Data Table nodes:
   - `crisislink_incidents`: received_at (date), last_report_at (date), report_count (number), chat_id, input_type, priority, priority_color, depth_cm (number), depth_confidence, victim_count (number), trapped (boolean), medical_flag (boolean), rescue_asset, escalate_to_human (boolean), guardrail_notes, reasoning, transcript, asr_engine, visual_cues, photo_file_id, vision_json, audio_json, latitude (number), longitude (number), location_accuracy_m (number), location_source, maps_link, location_updated_at (date), closed (boolean). Unlisted types are string.
   - `crisislink_chat_locations`: chat_id, latitude (number), longitude (number), accuracy_m (number), is_live (boolean), location_updated_at (date).
5. **Publish** the workflow. This registers the Telegram webhook, so republish whenever the public URL changes.

### 4. Run

Send the bot a flood photo (a caption is analysed too), a voice note or a text. You receive an acknowledgement at once, then the incident ticket; the row appears in `crisislink_incidents`. Tap "Share my location" (Telegram mobile app only) to attach GPS.

Reports from the same chat within 30 minutes are merged into one incident ("update #2", ...). Send **/new** to close it and start a fresh incident, for example between two demo scenarios.

## Evaluations (deliverable 4 and supporting evidence)

```powershell
python rag/evaluate.py          # chunking x embedding benchmark   -> rag/results/retrieval_eval.md
python eval/vision_eval.py      # vision prompt V1 vs V2           -> eval/results/vision_eval.md
python eval/extractor_eval.py   # extractor prompt V2 vs V3 vs V4  -> eval/results/extractor_eval.md
```

## Operating notes

- **Model retirements.** Groq and Google retire models. Each model name is a constant at the top of its Code node (`Build Vision Request`, `Build Gemini Request`, `Build Extraction Request`) or in the Groq Chat Model node.
- **Free-tier limits.** Gemini returns 429 when rate-limited; the workflow then falls back to Whisper automatically (`asr_engine` on the board shows which one ran). The Groq vision model allows 200,000 tokens per day (about 70-100 photos). Run the evaluations with a separate key (`groq_eval_api_key` in `.env`) so they never use up the demo key's quota.
- **One editor at a time.** Saving the workflow from a stale n8n browser tab overwrites newer changes. Reload the tab before saving.
