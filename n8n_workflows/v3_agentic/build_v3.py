"""Builds the CrisisLink v3 agentic workflows (n8n 2.43) from prompts and code kept as plain files.

Outputs (in this folder):
  crisislink_v3_agentic.json          main workflow: Telegram Trigger -> Triage Orchestrator (multi-agent)
  crisislink_tool_transcribe_gemini.json   sub-workflow tool used by the Distress Agent
  crisislink_tool_transcribe_whisper.json  sub-workflow tool used by the Distress Agent (backup engine)

Usage: python n8n_workflows/v3_agentic/build_v3.py
"""
import json
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OLD = json.loads((ROOT / 'n8n_workflows' / 'crisislink_workflow.json').read_text(encoding='utf-8'))
OLD_NODES = {n['name']: n for n in OLD['nodes']}

# Credentials and Data Tables of the existing instance (same as workflow v2)
CRED = {
    'telegram': {'telegramApi': {'id': 'TD9NIys0aw9ptA4p', 'name': 'Telegram account'}},
    'groq': {'groqApi': {'id': 'v5t30bH4LWNDBwUP', 'name': 'Groq account'}},
    'gemini': {'googlePalmApi': {'id': 'Iv6cmEx1jRRgpWYT', 'name': 'Google Gemini(PaLM) Api account'}},
    'bearer': {'httpBearerAuth': {'id': 'xg45srGOXb1ejgPE', 'name': 'Bearer Auth account'}},
    'qdrant': {'qdrantApi': {'id': 'RztXBvuc536lbZtF', 'name': 'Qdrant account'}},
    'hf': {'huggingFaceApi': {'id': 'DgeFIPGoFOM4LTzF', 'name': 'Hugging Face account'}},
}
INCIDENTS = {'__rl': True, 'mode': 'id', 'value': 'QCEMSYshy5LRB8Ja', 'cachedResultName': 'crisislink_incidents'}
LOCATIONS = {'__rl': True, 'mode': 'id', 'value': 'KhPn7esMmLaEIMyV', 'cachedResultName': 'crisislink_chat_locations'}

# Fixed ids so the main workflow can reference the tool sub-workflows after a CLI import
WF_MAIN = 'CLv3AgenticMain1'
WF_GEMINI = 'CLv3ToolGemini01'
WF_WHISPER = 'CLv3ToolWhisper1'

MSG = "$('Telegram Trigger').first().json.message"
CHAT = "String(" + MSG + ".chat.id)"

P = lambda name: (HERE / 'prompts' / name).read_text(encoding='utf-8').strip()


def nid():
    return str(uuid.uuid4())


def node(name, type_, version, pos, params, creds=None, **extra):
    n = {'parameters': params, 'id': nid(), 'name': name, 'type': type_, 'typeVersion': version, 'position': pos}
    if creds:
        n['credentials'] = CRED[creds]
    n.update(extra)
    return n


def groq(name, model, pos):
    return node(name, '@n8n/n8n-nodes-langchain.lmChatGroq', 1, pos, {'model': model, 'options': {'temperature': 0.1}}, 'groq')


def gemini(name, model, pos):
    return node(name, '@n8n/n8n-nodes-langchain.lmChatGoogleGemini', 1.1, pos, {'modelName': 'models/' + model, 'options': {'temperature': 0.1}}, 'gemini')


def col_schema(cols):
    return [{'id': c, 'displayName': c, 'required': False, 'defaultMatch': False, 'display': True, 'type': t, 'canBeUsedToMatch': True} for c, t in cols]


def fromai(key, desc, typ='string'):
    desc = desc.replace("'", '`')
    return "$fromAI('%s', '%s', '%s')" % (key, desc, typ)


def nullable_number(key, desc):
    f = fromai(key, desc + ' Use -1 if unknown.', 'number')
    return '={{ %s >= 0 ? %s : null }}' % (f, f)


# ------------------------------------------------------------------ main workflow
nodes, conns = [], {}


def link(src, dst, kind, index=0):
    conns.setdefault(src, {}).setdefault(kind, [[]])[0].append({'node': dst, 'type': kind, 'index': index})


trigger = node('Telegram Trigger', 'n8n-nodes-base.telegramTrigger', 1.5, [0, 0],
               {'updates': ['message'], 'additionalFields': {'download': True, 'imageSize': 'large'}}, 'telegram',
               webhookId=nid(), notes='Downloads photos so the Vision Agent can see them; voice notes are fetched by the transcription tools')
nodes.append(trigger)

user_msg = (
    "={{ JSON.stringify({\n"
    "  chat_id: String($json.message.chat.id),\n"
    "  received_at: $now.toISO(),\n"
    "  text: $json.message.text || null,\n"
    "  caption: $json.message.caption || null,\n"
    "  photo_attached: !!($json.message.photo || (($json.message.document || {}).mime_type || '').startsWith('image/')),\n"
    "  photo_file_id: $json.message.photo ? $json.message.photo[$json.message.photo.length - 1].file_id : null,\n"
    "  language_code: $json.message.from.language_code || null,\n"
    "  voice_note_attached: !!($json.message.voice || $json.message.audio),\n"
    "  location: $json.message.location ? { latitude: $json.message.location.latitude, longitude: $json.message.location.longitude } : null,\n"
    "  other_content: Object.keys($json.message).filter(k => ['sticker','video','video_note','contact','poll','animation','document'].includes(k))\n"
    "}, null, 1) }}"
)
orch = node('Triage Orchestrator', '@n8n/n8n-nodes-langchain.agent', 3.1, [320, 0],
            {'promptType': 'define', 'text': user_msg, 'needsFallback': True,
             'options': {'systemMessage': P('orchestrator.txt'), 'maxIterations': 15, 'returnIntermediateSteps': True,
                         'passthroughBinaryImages': False}},
            notes='Master agent: decides what the message is, which specialists to call, fuses the incident, writes the board and replies')
nodes.append(orch)
link('Telegram Trigger', 'Triage Orchestrator', 'main')
conns['Telegram Trigger'] = {'main': [[{'node': 'Triage Orchestrator', 'type': 'main', 'index': 0}]]}
conns = {k: v for k, v in conns.items()}

nodes += [gemini('Gemini 3.8 Flash (orchestrator)', 'gemini-3.8-flash', [120, 260]),
          gemini('Gemini 3.1 Flash-Lite (orchestrator fallback)', 'gemini-3.1-flash-lite', [260, 260])]
link('Gemini 3.8 Flash (orchestrator)', 'Triage Orchestrator', 'ai_languageModel', 0)
link('Gemini 3.1 Flash-Lite (orchestrator fallback)', 'Triage Orchestrator', 'ai_languageModel', 1)

# --- Vision Agent (agent tool; sees the photo downloaded by the trigger)
vision = node('Vision Agent', '@n8n/n8n-nodes-langchain.agentTool', 3, [420, 260], {
    'toolDescription': 'Specialist agent that analyses the photo attached to the citizen message: is it a flood, water depth in cm from reference anchors, confidence, visual cues, moving water, people visible. Call it only when photo_attached is true. Input: what you want to know. Returns the Vision Assessment JSON.',
    'text': "=Request from the orchestrator: {{ " + fromai('request', 'What you need to know about the attached photo') + " }}\nCitizen caption: {{ " + MSG + ".caption || '(none)' }}\nAnalyse the attached photo and return the vision JSON.",
    'hasOutputParser': True, 'needsFallback': True,
    'options': {'systemMessage': P('vision_agent.txt'), 'maxIterations': 6, 'passthroughBinaryImages': True}})
nodes.append(vision)
link('Vision Agent', 'Triage Orchestrator', 'ai_tool')
nodes += [groq('Groq Qwen 3.8 27B (vision)', 'qwen/qwen3.8-27b', [300, 520]),
          gemini('Gemini 3.5 Flash-Lite (vision fallback)', 'gemini-3.5-flash-lite', [420, 520])]
link('Groq Qwen 3.8 27B (vision)', 'Vision Agent', 'ai_languageModel', 0)
link('Gemini 3.5 Flash-Lite (vision fallback)', 'Vision Agent', 'ai_languageModel', 1)
o = OLD_NODES['lookup_reference_height']
nodes.append(node('lookup_reference_height', o['type'], o['typeVersion'], [540, 520], o['parameters']))
link('lookup_reference_height', 'Vision Agent', 'ai_tool')
o = OLD_NODES['Vision Output Parser']
nodes.append(node('Vision Output Parser', o['type'], o['typeVersion'], [660, 520], o['parameters']))
link('Vision Output Parser', 'Vision Agent', 'ai_outputParser')

# --- Distress Agent (agent tool; reads the raw citizen words straight from the trigger, never a paraphrase)
distress = node('Distress Agent', '@n8n/n8n-nodes-langchain.agentTool', 3, [820, 260], {
    'toolDescription': 'Specialist agent for the citizen words: transcribes the voice note itself if there is one, reads the text or caption (Tunisian Derja, French, English), and extracts victims, trapped status, vulnerable persons, reported depth and whether it is a genuine emergency. It may send the citizen ONE follow-up question. Call it whenever there is a text, a caption or a voice note. Returns the Distress JSON.',
    'text': "=follow_up_allowed: {{ " + fromai('follow_up_allowed', 'false if the open incident already has followup_asked = true, otherwise true', 'boolean') + " }}\nvoice_note_attached: {{ !!(" + MSG + ".voice || " + MSG + ".audio) }}\nCitizen text or caption (verbatim):\n\"\"\"\n{{ " + MSG + ".text || " + MSG + ".caption || '(none)' }}\n\"\"\"",
    'hasOutputParser': True,
    'options': {'systemMessage': P('distress_agent.txt'), 'maxIterations': 8}})
nodes.append(distress)
link('Distress Agent', 'Triage Orchestrator', 'ai_tool')
nodes.append(groq('Groq gpt-oss-120b (distress)', 'openai/gpt-oss-120b', [700, 780]))
link('Groq gpt-oss-120b (distress)', 'Distress Agent', 'ai_languageModel')

FILE_ID = "={{ " + MSG + ".voice ? " + MSG + ".voice.file_id : (" + MSG + ".audio ? " + MSG + ".audio.file_id : '') }}"


def wf_tool(name, desc, wf_id, wf_name, pos):
    return node(name, '@n8n/n8n-nodes-langchain.toolWorkflow', 2.2, pos, {
        'description': desc,
        'workflowId': {'__rl': True, 'mode': 'list', 'value': wf_id, 'cachedResultName': wf_name},
        'workflowInputs': {'mappingMode': 'defineBelow', 'value': {'file_id': FILE_ID}, 'matchingColumns': [],
                           'schema': [{'id': 'file_id', 'displayName': 'file_id', 'required': False, 'defaultMatch': False, 'display': True,
                                       'canBeUsedToMatch': True, 'type': 'string', 'removed': False}],
                           'attemptToConvertTypes': False, 'convertFieldsToString': False}})


nodes.append(wf_tool('transcribe_voice', 'Transcribes the voice note of this citizen message with Gemini 3.5 Transcribe (best for Tunisian Derja). Returns {text, asr_engine}. Call it first when voice_note_attached is true.',
                     WF_GEMINI, 'CrisisLink Tool - Transcribe (Gemini)', [820, 780]))
nodes.append(wf_tool('transcribe_voice_backup', 'Backup transcription of the same voice note with Whisper large-v3. Call it ONLY if transcribe_voice failed or returned empty text.',
                     WF_WHISPER, 'CrisisLink Tool - Transcribe (Whisper)', [940, 780]))
link('transcribe_voice', 'Distress Agent', 'ai_tool')
link('transcribe_voice_backup', 'Distress Agent', 'ai_tool')
o = OLD_NODES['convert_level_to_cm']
nodes.append(node('convert_level_to_cm', o['type'], o['typeVersion'], [1060, 780], o['parameters']))
link('convert_level_to_cm', 'Distress Agent', 'ai_tool')
o = OLD_NODES['ask_citizen']
p = json.loads(json.dumps(o['parameters']))
p['chatId'] = '={{ ' + CHAT + ' }}'
nodes.append(node('ask_citizen', o['type'], o['typeVersion'], [1180, 780], p, 'telegram'))
link('ask_citizen', 'Distress Agent', 'ai_tool')
schema = json.loads(OLD_NODES['Distress Output Parser']['parameters']['inputSchema'])
schema['properties'].update({
    'transcript': {'type': 'string', 'description': 'verbatim transcript of the voice note, or the text/caption'},
    'asr_engine': {'type': 'string', 'description': 'gemini-3.5-transcribe, whisper-large-v3, or none (text)'},
    'transcription_failed': {'type': 'boolean'},
    'followup_asked': {'type': 'boolean', 'description': 'true only if you called ask_citizen'},
})
schema['required'] += ['transcript', 'asr_engine', 'followup_asked']
nodes.append(node('Distress Output Parser', '@n8n/n8n-nodes-langchain.outputParserStructured', 1.3, [1300, 780],
                  {'schemaType': 'manual', 'inputSchema': json.dumps(schema, ensure_ascii=False, indent=1)}))
link('Distress Output Parser', 'Distress Agent', 'ai_outputParser')

# --- Protocol Agent (agentic RAG)
proto = node('Protocol Agent', '@n8n/n8n-nodes-langchain.agentTool', 3, [1220, 260], {
    'toolDescription': 'Specialist agent for the official flood protocols (priority tiers P1-P4, rescue asset per tier, hard safety rules, hazard thresholds, advice for trapped citizens, Tunisian Civil Protection guidance). Ask it one question describing the depth and circumstances. Returns the applicable rules quoted from the knowledge base.',
    'text': "={{ " + fromai('question', 'Your question about the protocols, with the depth and circumstances') + " }}",
    'options': {'systemMessage': P('protocol_agent.txt'), 'maxIterations': 4}})
nodes.append(proto)
link('Protocol Agent', 'Triage Orchestrator', 'ai_tool')
nodes.append(groq('Groq gpt-oss-20b (protocol)', 'openai/gpt-oss-20b', [1140, 520]))
link('Groq gpt-oss-20b (protocol)', 'Protocol Agent', 'ai_languageModel')
o = OLD_NODES['Search Flood Protocols']
sp = json.loads(json.dumps(o['parameters']))
sp['qdrantCollection'] = {'__rl': True, 'mode': 'id', 'value': 'structured_index_gemini', 'cachedResultName': 'structured_index_gemini'}
nodes.append(node('Search Flood Protocols', o['type'], o['typeVersion'], [1280, 520], sp, 'qdrant'))
link('Search Flood Protocols', 'Protocol Agent', 'ai_tool')
# Embeddings: Hugging Face's hosted API ran out of free credits, so the index was rebuilt with Google's gemini-embedding-001
# (native n8n node, same Gemini credential, better on our benchmark: rag/results/retrieval_eval_gemini.md)
nodes.append(node('Embeddings (gemini-embedding-001)', '@n8n/n8n-nodes-langchain.embeddingsGoogleGemini', 1,
                  [1280, 700], {'modelName': 'models/gemini-embedding-001'}, 'gemini'))
link('Embeddings (gemini-embedding-001)', 'Search Flood Protocols', 'ai_embedding')

# --- Safety Officer (agent + deterministic rules tool)
safety = node('Safety Officer', '@n8n/n8n-nodes-langchain.agentTool', 3, [1620, 260], {
    'toolDescription': 'Safety Officer agent. Give it your draft decision and every specialist result of the incident; it checks them with the deterministic CrisisLink safety rules and returns the FINAL decision (it can only raise the priority or require human review) and the ticket text to send. Always call it before saving or replying.',
    'text': "=DRAFT_DECISION: {{ " + fromai('draft_decision', 'Your draft as JSON: priority, rescue_asset, conflict_detected, escalate_to_human, situation_summary, citizen_safety_advice, reasoning') + " }}\n"
            "VISION_REPORTS: {{ " + fromai('vision_reports', 'JSON array of every Vision Agent result of this incident, previous (merged_vision_json of the open incident) and current, verbatim; [] if none') + " }}\n"
            "DISTRESS_REPORTS: {{ " + fromai('distress_reports', 'JSON array of every Distress Agent result of this incident, previous (merged_distress_json of the open incident) and current, verbatim; [] if none') + " }}\n"
            "REPORT_COUNT: {{ " + fromai('report_count', 'Number of reports in this incident including this one', 'number') + " }}\n"
            "MAPS_LINK: {{ " + fromai('maps_link', 'Google Maps link of the citizen location, or empty') + " }}\n"
            "LANG: {{ " + fromai('lang', 'Language of the citizen: en, fr or ar') + " }}\n"
            "CITIZEN_WORDS (verbatim from Telegram): {{ " + MSG + ".text || " + MSG + ".caption || '(none)' }}",
    'needsFallback': True,
    'options': {'systemMessage': P('safety_officer.txt'), 'maxIterations': 4}})
nodes.append(safety)
link('Safety Officer', 'Triage Orchestrator', 'ai_tool')
nodes += [gemini('Gemini 3.1 Flash-Lite (safety)', 'gemini-3.1-flash-lite', [1540, 520]),
          groq('Groq gpt-oss-20b (safety fallback)', 'openai/gpt-oss-20b', [1660, 520])]
link('Gemini 3.1 Flash-Lite (safety)', 'Safety Officer', 'ai_languageModel', 0)
link('Groq gpt-oss-20b (safety fallback)', 'Safety Officer', 'ai_languageModel', 1)
nodes.append(node('check_triage_rules', '@n8n/n8n-nodes-langchain.toolCode', 1.3, [1780, 520], {
    'description': 'Deterministic CrisisLink safety rules. Input: ONE JSON string {"draft": {...}, "vision_reports": [...], "distress_reports": [...], "citizen_texts": "...", "report_count": n, "maps_link": "..."}. Output: the final decision JSON with ticket_text. The priority it returns can only be equal to or higher than the draft.',
    'jsCode': (HERE / 'check_triage_rules.js').read_text(encoding='utf-8')}))
link('check_triage_rules', 'Safety Officer', 'ai_tool')

# --- Incident memory tools (Data Tables). Chat id is hard-wired: an agent can only touch its own citizen's rows
INC_COLS = [('received_at', 'dateTime'), ('last_report_at', 'dateTime'), ('report_count', 'number'), ('chat_id', 'string'), ('input_type', 'string'),
            ('priority', 'string'), ('priority_color', 'string'), ('depth_cm', 'number'), ('depth_confidence', 'string'), ('victim_count', 'number'),
            ('trapped', 'boolean'), ('medical_flag', 'boolean'), ('rescue_asset', 'string'), ('escalate_to_human', 'boolean'), ('guardrail_notes', 'string'),
            ('reasoning', 'string'), ('transcript', 'string'), ('asr_engine', 'string'), ('visual_cues', 'string'), ('photo_file_id', 'string'),
            ('vision_json', 'string'), ('audio_json', 'string'), ('followup_asked', 'boolean'), ('latitude', 'number'), ('longitude', 'number'),
            ('maps_link', 'string'), ('location_source', 'string'), ('closed', 'boolean')]


def dt_tool(name, desc, params, pos):
    params = {'descriptionType': 'manual', 'toolDescription': desc, **params}
    return node(name, 'n8n-nodes-base.dataTableTool', 1.1, pos, params)


nodes.append(dt_tool('load_open_incident', 'Returns the open incident of this citizen (last report less than 30 minutes ago, not closed), or nothing if there is none. Its id, report_count, followup_asked, vision_json (merged vision) and audio_json (merged distress) are needed to update it.', {
    'operation': 'get', 'dataTableId': INCIDENTS, 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyName': 'chat_id', 'keyValue': '={{ ' + CHAT + ' }}'},
                               {'keyName': 'last_report_at', 'condition': 'gte', 'keyValue': '={{ $now.minus({ minutes: 30 }).toISO() }}'},
                               {'keyName': 'closed', 'condition': 'neq', 'keyValue': 'true'}]},
    'limit': 1, 'orderBy': True, 'orderByColumn': 'last_report_at'}, [1900, 260]))

save_vals = {
    'chat_id': '={{ ' + CHAT + ' }}',
    'last_report_at': '={{ $now.toISO() }}',
    'received_at': '={{ ' + fromai('received_at', 'received_at of the open incident, or the received_at of this message for a new incident (ISO time)') + ' }}',
    'report_count': '={{ ' + fromai('report_count', 'Number of reports in the incident including this one', 'number') + ' }}',
    'input_type': '={{ ' + fromai('input_type', 'Media types received so far, e.g. photo+voice') + ' }}',
    'priority': '={{ ' + fromai('priority', 'FINAL priority from the Safety Officer: P1, P2, P3 or P4') + ' }}',
    'priority_color': '={{ ' + fromai('priority_color', 'priority_color from the Safety Officer') + ' }}',
    'depth_cm': nullable_number('depth_cm', 'depth_cm from the Safety Officer.'),
    'depth_confidence': '={{ ' + fromai('depth_confidence', 'depth_confidence from the Safety Officer') + ' }}',
    'victim_count': nullable_number('victim_count', 'victim_count from the Safety Officer.'),
    'trapped': '={{ ' + fromai('trapped', 'trapped from the Safety Officer', 'boolean') + ' }}',
    'medical_flag': '={{ ' + fromai('medical_flag', 'medical_flag from the Safety Officer', 'boolean') + ' }}',
    'rescue_asset': '={{ ' + fromai('rescue_asset', 'rescue_asset from the Safety Officer') + ' }}',
    'escalate_to_human': '={{ ' + fromai('escalate_to_human', 'escalate_to_human from the Safety Officer', 'boolean') + ' }}',
    'guardrail_notes': '={{ ' + fromai('guardrail_notes', 'guardrail_notes from the Safety Officer') + ' }}',
    'reasoning': '={{ ' + fromai('reasoning', 'Short summary of how the team reached the decision (which agents, which protocol)') + ' }}',
    'transcript': '={{ ' + fromai('transcript', 'transcript from the Safety Officer') + ' }}',
    'asr_engine': '={{ ' + fromai('asr_engine', 'asr_engine from the Safety Officer') + ' }}',
    'visual_cues': '={{ ' + fromai('visual_cues', 'visual_cues from the Safety Officer') + ' }}',
    'photo_file_id': '={{ ' + fromai('photo_file_id', 'photo_file_id of this message, or the one of the open incident, or empty') + ' }}',
    'vision_json': '={{ ' + fromai('vision_json', 'merged_vision_json from the Safety Officer, verbatim') + ' }}',
    'audio_json': '={{ ' + fromai('audio_json', 'merged_distress_json from the Safety Officer, verbatim') + ' }}',
    'followup_asked': '={{ ' + fromai('followup_asked', 'followup_asked from the Safety Officer, or true if the open incident already had it', 'boolean') + ' }}',
    'latitude': nullable_number('latitude', 'Latitude of the citizen if known.'),
    'longitude': nullable_number('longitude', 'Longitude of the citizen if known.'),
    'maps_link': '={{ ' + fromai('maps_link', 'Google Maps link if the location is known, else empty') + ' }}',
    'location_source': '={{ ' + fromai('location_source', 'gps if the location is known, else empty') + ' }}',
    'closed': '={{ false }}',
}
nodes.append(dt_tool('save_incident', 'Creates or updates the incident row on the dispatcher board with the FINAL decision of the Safety Officer. Use incident_id = id of the open incident, or -1 to create a new one.', {
    'operation': 'upsert', 'dataTableId': INCIDENTS, 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyValue': '={{ ' + fromai('incident_id', 'id of the open incident, or -1 for a new incident', 'number') + ' }}'}]},
    'columns': {'mappingMode': 'defineBelow', 'value': save_vals, 'matchingColumns': [], 'schema': col_schema(INC_COLS),
                'attemptToConvertTypes': False, 'convertFieldsToString': False}}, [2020, 260]))

nodes.append(dt_tool('close_open_incident', 'Closes the open incident of this citizen (used for the /new command), so the next report starts a new incident.', {
    'operation': 'update', 'dataTableId': INCIDENTS, 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyName': 'chat_id', 'keyValue': '={{ ' + CHAT + ' }}'},
                               {'keyName': 'last_report_at', 'condition': 'gte', 'keyValue': '={{ $now.minus({ minutes: 30 }).toISO() }}'}]},
    'columns': {'mappingMode': 'defineBelow', 'matchingColumns': [], 'value': {'closed': True}, 'schema': col_schema([('closed', 'boolean')])},
    'options': {}}, [2140, 260]))

LOC = MSG + '.location'
nodes.append(dt_tool('save_chat_location', 'Saves the GPS location the citizen just shared (only when the message contains a location). Takes no input: the coordinates are read from the message.', {
    'operation': 'upsert', 'dataTableId': LOCATIONS, 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyName': 'chat_id', 'keyValue': '={{ ' + CHAT + ' }}'}]},
    'columns': {'mappingMode': 'defineBelow', 'matchingColumns': [], 'value': {
        'chat_id': '={{ ' + CHAT + ' }}', 'latitude': '={{ ' + LOC + '.latitude }}', 'longitude': '={{ ' + LOC + '.longitude }}',
        'accuracy_m': '={{ ' + LOC + '.horizontal_accuracy || null }}', 'is_live': '={{ !!' + LOC + '.live_period }}',
        'location_updated_at': '={{ $now.toISO() }}'},
        'schema': col_schema([('chat_id', 'string'), ('latitude', 'number'), ('longitude', 'number'), ('accuracy_m', 'number'), ('is_live', 'boolean'), ('location_updated_at', 'dateTime')])}},
    [2260, 260]))
nodes.append(dt_tool('get_chat_location', 'Returns the last GPS location this citizen shared (latitude, longitude), or nothing.', {
    'operation': 'get', 'dataTableId': LOCATIONS, 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyName': 'chat_id', 'keyValue': '={{ ' + CHAT + ' }}'}]}, 'limit': 1}, [2380, 260]))

# --- Telegram tools (chat id hard-wired to the sender)
nodes.append(node('send_message', 'n8n-nodes-base.telegramTool', 1.2, [2500, 260], {
    'descriptionType': 'manual',
    'toolDescription': 'Sends a message to the citizen who wrote (acknowledgement, confirmation, or the ticket_text of the Safety Officer). Telegram HTML: only <b> and <i>; escape < > & in normal text.',
    'chatId': '={{ ' + CHAT + ' }}',
    'text': '={{ ' + fromai('text', 'The message to send') + ' }}',
    'additionalFields': {'appendAttribution': False, 'parse_mode': 'HTML'}}, 'telegram'))
o = OLD_NODES['Request Location']
p = json.loads(json.dumps(o['parameters']))
p['chatId'] = '={{ ' + CHAT + ' }}'
p = {'descriptionType': 'manual', 'toolDescription': 'Sends the citizen a button to share their GPS location. Takes no input. Use once per incident when no location is known.', **p}
nodes.append(node('request_location', 'n8n-nodes-base.telegramTool', 1.2, [2620, 260], p, 'telegram'))
for t in ('load_open_incident', 'save_incident', 'close_open_incident', 'save_chat_location', 'get_chat_location', 'send_message', 'request_location'):
    link(t, 'Triage Orchestrator', 'ai_tool')

nodes.append(node('Note', 'n8n-nodes-base.stickyNote', 1, [-40, -260], {
    'content': '## CrisisLink v3 - agentic\nTelegram -> **Triage Orchestrator** (Gemini 3.8 Flash). No router, no IF: the orchestrator decides what the message is and which agents to call.\n\nAgents (agent-to-agent tool calls): **Vision Agent**, **Distress Agent**, **Protocol Agent** (RAG), **Safety Officer** (deterministic rules tool).\nMemory and output are tools too: incident board, locations, Telegram.',
    'height': 220, 'width': 640}))

main = {'id': WF_MAIN, 'name': 'CrisisLink v3 - Agentic Triage', 'nodes': nodes, 'connections': conns, 'active': False,
        'settings': {'executionOrder': 'v1', 'binaryMode': 'separate'}, 'pinData': {}, 'meta': {'templateCredsSetupCompleted': True}, 'tags': []}

# ------------------------------------------------------------------ transcription tool sub-workflows


def sub_trigger(pos):
    return node('When called by the Distress Agent', 'n8n-nodes-base.executeWorkflowTrigger', 1.1, pos,
                {'workflowInputs': {'values': [{'name': 'file_id'}]}})


def download(pos):
    return node('Download Voice', 'n8n-nodes-base.telegram', 1.2, pos, {'resource': 'file', 'fileId': '={{ $json.file_id }}', 'additionalFields': {}}, 'telegram')


def chain(names):
    return {a: {'main': [[{'node': b, 'type': 'main', 'index': 0}]]} for a, b in zip(names, names[1:])}


o = OLD_NODES
g_nodes = [sub_trigger([0, 0]), download([220, 0]),
           node('Build Gemini Request', 'n8n-nodes-base.code', 2, [440, 0], o['Build Gemini Request']['parameters']),
           node('Gemini Transcribe', 'n8n-nodes-base.httpRequest', 4.2, [660, 0], o['Gemini Transcribe']['parameters'], 'gemini'),
           node('Parse Gemini Transcript', 'n8n-nodes-base.code', 2, [880, 0], {'jsCode': o['Parse Gemini Transcript']['parameters']['jsCode'].replace(
               "return { json: { text, asr_engine: 'gemini-3.5-transcribe' } };",
               "if (!text) throw new Error('Gemini returned an empty transcript: call transcribe_voice_backup');\nreturn { json: { text, asr_engine: 'gemini-3.5-transcribe' } };")})]
gem_wf = {'id': WF_GEMINI, 'name': 'CrisisLink Tool - Transcribe (Gemini)', 'nodes': g_nodes,
          'connections': chain([n['name'] for n in g_nodes]), 'active': False, 'settings': {'executionOrder': 'v1', 'callerPolicy': 'workflowsFromSameOwner'}, 'pinData': {}, 'tags': []}

w_nodes = [sub_trigger([0, 0]), download([220, 0]),
           node('Fix Audio Filename', 'n8n-nodes-base.code', 2, [440, 0], o['Fix Audio Filename']['parameters']),
           node('Whisper Transcribe', 'n8n-nodes-base.httpRequest', 4.5, [660, 0], o['Whisper Transcribe']['parameters'], 'bearer'),
           node('Result', 'n8n-nodes-base.set', 3.4, [880, 0], {'assignments': {'assignments': [
               {'id': nid(), 'name': 'text', 'value': '={{ $json.text }}', 'type': 'string'},
               {'id': nid(), 'name': 'asr_engine', 'value': 'whisper-large-v3', 'type': 'string'}]}, 'options': {}})]
wh_wf = {'id': WF_WHISPER, 'name': 'CrisisLink Tool - Transcribe (Whisper)', 'nodes': w_nodes,
         'connections': chain([n['name'] for n in w_nodes]), 'active': False, 'settings': {'executionOrder': 'v1', 'callerPolicy': 'workflowsFromSameOwner'}, 'pinData': {}, 'tags': []}

for fname, wf in (('crisislink_v3_agentic.json', main), ('crisislink_tool_transcribe_gemini.json', gem_wf), ('crisislink_tool_transcribe_whisper.json', wh_wf)):
    (HERE / fname).write_text(json.dumps(wf, ensure_ascii=False, indent=1), encoding='utf-8')
    print(fname, len(wf['nodes']), 'nodes')
