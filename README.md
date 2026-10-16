# CrisisLink-5DS

Citizen-to-Civil-Defense multimodal flood triage. A citizen sends a **photo**, a **voice note** (Tunisian Derja, French or English), a **text** or their **GPS location** to a Telegram bot. A team of AI agents estimates the water depth, extracts who is in danger, retrieves the official flood protocols, grades the incident **P1-P4**, checks the decision with deterministic safety rules, and posts a structured ticket to a dispatcher board and back to the citizen **in their own language** (English, French or Arabic).

Esprit 5DS - Advanced Deep Learning final project.

Repository: https://github.com/Aymenrahmanii/CrisisLink-5DS  |  Project files to import: `n8n_workflows/v3_agentic/*.json`  |  Report and slides: `docs/`

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

### Prerequisites

| Item | Version / note |
|---|---|
| Node.js | 20.19 or later (22 recommended), to run n8n with `npx n8n` |
| n8n | 2.43 or later (tested on 2.43.7); needs the AI Agent Tool, Data Tables and Execute Workflow nodes |
| Python | 3.10 or later, only for the knowledge-base and evaluation scripts |
| cloudflared | Optional but recommended: gives n8n a public HTTPS URL so Telegram can reach it (`start_crisislink.ps1` uses it) |
| Accounts (all free tiers) | Telegram, Groq, Google AI Studio, Qdrant Cloud |

### Quick start

1. Clone the repository and open a terminal in its folder.
2. Create the four accounts below and keep the keys at hand.
3. Fill in `.env` and build the knowledge base (step 2).
4. Start n8n (step 3.1).
5. Import the three workflows in the given order (step 3.2).
6. Select your credentials in the nodes that show a warning (step 3.3).
7. **Publish the two transcription workflows** (step 3.4).
8. Create the two Data Tables and select them in the Data Table tools (step 3.5).
9. Check the Qdrant collection and the embeddings node, then **publish the main workflow** (steps 3.6 and 3.7).
10. Send the bot a message and compare with "Check that it works" below.

### 1. Accounts and keys

| Service | Used for | Where the key goes |
|---|---|---|
| Telegram @BotFather (`/newbot`) | Citizen chat bot | n8n credential "Telegram account" |
| Groq (console.groq.com) | Qwen vision, gpt-oss agents, Whisper backup | n8n credential "Groq account" (Groq type) and "Bearer Auth account" (HTTP Bearer, same key, used by the Whisper tool) |
| Google AI Studio (aistudio.google.com) | Gemini agents, Gemini 3.5 Transcribe, Gemini embeddings | n8n credential "Google Gemini(PaLM) Api account" |
| Qdrant Cloud (free cluster) | Vector store | n8n credential "Qdrant account" (cluster URL and API key) |

For the Python scripts copy `.env.example` to `.env` and fill in `qdrant` (API key), `qdrant_end_point` (cluster URL), `telegram_bot_token`, `groq_api_key`, `gemini_api_key` and `groq_eval_api_key` (a second Groq key for the evaluations; the same key works if you only run the demo). `.env` is git-ignored.

### 2. Knowledge base (once)

```powershell
pip install sentence-transformers qdrant-client python-dotenv requests langchain-text-splitters
python rag/build_index_gemini.py     # creates the Qdrant collection structured_index_gemini (used by the workflow)
```

Expected output: `structured_index_gemini: 24 chunks indexed (3072 dimensions)`.

### 3. n8n

1. Start n8n: `npx n8n`, or `powershell -ExecutionPolicy Bypass -File .\start_crisislink.ps1`, which also opens a public Cloudflare tunnel and starts n8n with the matching webhook URL. Telegram needs a public HTTPS address, and a quick tunnel gets a new URL at every start, so republish the main workflow after a restart. n8n opens on http://localhost:5678.
2. **Workflows > Import from file**, in this order:
   1. `n8n_workflows/v3_agentic/crisislink_tool_transcribe_gemini.json`
   2. `n8n_workflows/v3_agentic/crisislink_tool_transcribe_whisper.json`
   3. `n8n_workflows/v3_agentic/crisislink_v3_agentic.json`

   (CLI alternative that keeps the workflow ids: copy the three files into one folder and run `n8n import:workflow --separate --input=<folder>`.)
3. Open every node with a credential warning and select your credential (Telegram, Groq, Google Gemini, Bearer Auth, Qdrant). Do this in the two transcription workflows as well (Telegram, Gemini and Bearer Auth nodes). In the main workflow, the tool nodes `transcribe_voice` and `transcribe_voice_backup` must point to the two imported transcription workflows (reselect them if n8n shows a warning).
4. **Publish both transcription workflows** (open each and click Publish). n8n refuses to call an unpublished workflow as a tool ("Workflow is not active and cannot be executed").
5. Create two **Data Tables** (they are not part of the export) and select them in the Data Table tool nodes (`load_open_incident`, `save_incident`, `close_open_incident`, `save_chat_location`, `get_chat_location`):
   - `crisislink_incidents`: `received_at`, `last_report_at` (date); `report_count`, `depth_cm`, `victim_count`, `latitude`, `longitude` (number); `trapped`, `medical_flag`, `escalate_to_human`, `followup_asked`, `closed` (boolean); and as string: `chat_id`, `input_type`, `priority`, `priority_color`, `depth_confidence`, `rescue_asset`, `guardrail_notes`, `reasoning`, `transcript`, `asr_engine`, `visual_cues`, `photo_file_id`, `vision_json`, `audio_json`, `maps_link`, `location_source`.
   - `crisislink_chat_locations`: `chat_id`; `latitude`, `longitude`, `accuracy_m` (number); `is_live` (boolean); `location_updated_at` (date).
6. In **Search Flood Protocols** check the collection is `structured_index_gemini`, and that **Embeddings (gemini-embedding-001)** is connected to it.
7. **Publish** `CrisisLink v3 - Agentic Triage`. This registers the Telegram webhook; only one workflow can own the bot, so keep the legacy workflow unpublished.

### 4. Use it

Send the bot a photo (a caption is analysed too), a voice note, a text or your location. You get an acknowledgement at once, then the incident ticket in your language; the row appears in `crisislink_incidents`. Tap "Share my location" (Telegram mobile app) to attach GPS. Reports from the same chat within 30 minutes are merged into one incident ("update #2", ...). Send **/new** to close it and start a fresh one, for example between two scenarios. Leave about a minute between reports: the free API tiers are rate-limited.

### Check that it works

Send `/new`, wait a few seconds, then send each message below.

| Send | Expected |
|---|---|
| `Au secours ! L'eau dépasse 120 cm, ma grand-mère de 80 ans est bloquée au premier étage.` | Acknowledgement, then a French ticket: **P1**, boat + paramedic team |
| `Au secours, l'eau monte vite dans la rue` | One follow-up question in French; answer `ma grand-mère est avec moi, on est bloqués` and the ticket becomes "mise à jour n°2", raised to **P1** |
| `الماء وصل فوق الكرهبة في نهجنا، فما مرا كبيرة معانا وما نجموش نخرجو` | Arabic ticket, **P1** |
| `hhhh c'est un test, l'eau c'est rien` | Low priority with **human review required** |
| the voice note `test_media/audio/01_distress_derja.mp3` | Transcript (Gemini), **P1** |
| a photo from `test_media/images/` | Depth estimate with an anchor, ticket graded by depth |

In n8n, **Executions** shows which agents were called; the `crisislink_incidents` Data Table shows one row per incident.

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Voice note not transcribed; "Workflow is not active and cannot be executed" | The two transcription workflows are not published (step 3.4) |
| Telegram never reaches n8n | The public URL changed or the workflow is unpublished: restart with `start_crisislink.ps1`, then unpublish and publish the main workflow |
| HTTP 429 / "too many requests" on a model | Free-tier rate limit: wait a minute between reports; the orchestrator, vision and safety agents fall back to another model automatically |
| Protocol Agent returns nothing useful | The embeddings node and the collection must match: `gemini-embedding-001` with `structured_index_gemini`. Do not mix with `structured_index` (e5 vectors) |
| Ticket mixes two scenarios | An incident from the last 30 minutes is still open: send `/new` |
| Edits disappear after saving | A stale n8n browser tab overwrote newer changes: reload the tab before saving |
| "A human operator will review" message and no ticket | The Safety Officer failed twice (usually a rate limit): resend after a minute |

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
