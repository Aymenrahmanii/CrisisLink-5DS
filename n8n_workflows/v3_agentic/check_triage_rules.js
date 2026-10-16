// check_triage_rules: the Safety Officer's deterministic tool. The LLMs propose, this code enforces.
// It can only RAISE the priority or ADD a human review, never lower either.
// Input (JSON string): { draft, vision_reports, distress_reports, citizen_texts, report_count, maps_link, lang: en|fr|ar }
const parse = (x) => {
  if (x === null || x === undefined || x === '') return null;
  if (typeof x !== 'string') return x;
  try { return JSON.parse(x); } catch (e) { return null; }
};
const inp = parse(query);
if (!inp || typeof inp !== 'object') {
  return 'ERROR: input must be one JSON object: {"draft": {...}, "vision_reports": [...], "distress_reports": [...], "citizen_texts": "...", "report_count": 1, "maps_link": ""}';
}
const list = (x) => { const v = parse(x); return (Array.isArray(v) ? v : v ? [v] : []).map(parse).filter((o) => o && typeof o === 'object'); };
const num = (x) => (x === null || x === undefined || x === '' || isNaN(Number(x)) ? null : Number(x));
const uniq = (a) => [...new Set(a.filter(Boolean))];
const t = parse(inp.draft) || {};
const visions = list(inp.vision_reports);
const distress = list(inp.distress_reports);

// 1. Fusion of every report of the incident (life-safety bias): deepest credible photo, max depth, max victims, OR of flags
const credible = (v) => v.is_flood !== false && v.confidence !== 'low' && num(v.estimated_depth_cm) !== null;
const vision = visions.length
  ? visions.reduce((best, v) => (!best ? v : (credible(v) ? num(v.estimated_depth_cm) : -1) >= (credible(best) ? num(best.estimated_depth_cm) : -1) ? v : best), null)
  : null;
const maxOf = (k) => { const v = distress.map((a) => num(a[k])).filter((x) => x !== null); return v.length ? Math.max(...v) : null; };
const audio = distress.length ? {
  transcript: uniq(distress.map((a) => a.transcript)).join(' || '),
  asr_engine: uniq(distress.map((a) => a.asr_engine)).join(', '),
  transcription_failed: distress.every((a) => a.transcription_failed === true),
  victim_count: maxOf('victim_count'),
  reported_depth_cm: maxOf('reported_depth_cm'),
  trapped: distress.some((a) => a.trapped === true),
  medical_flag: distress.some((a) => a.medical_flag === true),
  vulnerable_persons: uniq(distress.flatMap((a) => a.vulnerable_persons || [])),
  urgency_keywords: uniq(distress.flatMap((a) => a.urgency_keywords || [])),
  translation_en: uniq(distress.map((a) => a.translation_en)).join(' || '),
  is_genuine_emergency: distress.every((a) => a.is_genuine_emergency !== false),
  followup_asked: distress.some((a) => a.followup_asked === true),
} : null;

const RANK = { P1: 1, P2: 2, P3: 3, P4: 4 };
const LABEL = { P1: 'P1 - Critical / Immediate', P2: 'P2 - High / Urgent', P3: 'P3 - Moderate / Secondary', P4: 'P4 - Low / Monitoring' };
const COLOR = { P1: 'RED', P2: 'ORANGE', P3: 'YELLOW', P4: 'GREEN' };
const EMOJI = { P1: '🔴', P2: '🟠', P3: '🟡', P4: '🟢' };
const ASSET = {
  P1: 'Inflatable Rescue Boat (Zodiac) / Helicopter Hoist',
  P2: 'High-Clearance 4x4 Tactical Rescue Vehicle',
  P3: 'Tow Trucks / Road Closure Barricades',
  P4: 'Patrol Unit / Monitoring Drone',
};
const ASSET_P1_VULNERABLE = 'Inflatable Rescue Boat (Zodiac) + Paramedic Team';
const notes = [];

// 2. Multilingual keyword net on the citizens' own words (independent of the extractor LLM; tolerates both ASR spellings)
const text = [inp.citizen_texts, audio && audio.transcript, audio && audio.translation_en].filter(Boolean).join(' ').toLowerCase();
const KW = {
  trapped: /(ما ?ن?جم(ش|تش|وش|ناش) ?[تن]?خرج|ما ?ن?جمناش|ما ?[نت]قدرش ?[تن]خرج|محاصر|محصور|عالق|m7as?r|ma ?najm(ch|ech|nech|ouch)|coinc[ée]|bloqu[ée]|pi[ée]g[ée]|trapped|stuck|can'?t get out|cannot get out)/i,
  vulnerable: /(مر[اة] ?كبير|عجوز|شايب|شيخ|بيبي|رضيع|طفل|مريض|حامل|معاق|مجروح|3jouza|mra kbira|chayeb|b[ée]b[ée]|tfol|mrith|grand-m[èe]re|grand-p[èe]re|personne [âa]g[ée]e|vieill|enfant|nourrisson|enceinte|handicap|bless[ée]|elderly|old (wo)?man|grand(ma|pa|mother|father)|baby|infant|\bchild|\bkids?\b|pregnant|disabled|injured|\bsick\b)/i,
  deep: /(فوق ال?كر[ها]?ب|للصدر|السطح|fou9 el karhba|sadri|au-dessus de la voiture|jusqu'?[àa] la poitrine|sur le toit|over the car|above the car|up to (my |our )?chest|on the roof)/i,
};
const kw = { trapped: KW.trapped.test(text), vulnerable: KW.vulnerable.test(text), deep: KW.deep.test(text) };

// 3. Depth from evidence only: the draft's depth is never trusted
const vDepth = vision && vision.is_flood !== false ? num(vision.estimated_depth_cm) : null;
const aDepth = audio ? audio.reported_depth_cm : null;
const depths = [vDepth, aDepth].filter((d) => d !== null);
const depth = depths.length ? Math.max(...depths) : null;
const depthSource = vDepth !== null && aDepth !== null ? 'both' : vDepth !== null ? 'vision' : aDepth !== null ? 'audio' : 'none';

const extractorVulnerable = !!(audio && (audio.medical_flag || audio.vulnerable_persons.length));
const trapped = !!((audio && audio.trapped) || t.trapped === true || kw.trapped);
const vulnerable = extractorVulnerable || kw.vulnerable;
const medical = !!((audio && audio.medical_flag) || t.medical_flag === true || kw.vulnerable);

const kwMissed = [];
if (kw.trapped && !(audio && audio.trapped)) kwMissed.push('trapped');
if (kw.vulnerable && !extractorVulnerable) kwMissed.push('vulnerable person');
if (kw.deep && !(depth !== null && depth >= 100)) kwMissed.push('water above car / chest level');
if (kwMissed.length) notes.push('Keyword check caught what the specialists missed: ' + kwMissed.join(', '));

// 4. Start from the draft priority, fall back to the depth table
const draftPriority = RANK[t.priority] ? t.priority : null;
let priority = draftPriority;
if (!priority) {
  notes.push('Draft priority missing or invalid: deterministic fallback used');
  priority = depth === null ? 'P3' : depth > 100 ? 'P1' : depth >= 50 ? 'P2' : depth >= 20 ? 'P3' : 'P4';
}
const raiseTo = (target, why) => {
  if (RANK[priority] > RANK[target]) { notes.push(why + ': raised ' + priority + ' -> ' + target); priority = target; }
};
if (depth !== null && depth > 100) raiseTo('P1', 'Depth > 100 cm');
if (depth !== null && depth > 80) raiseTo('P2', 'Depth > 80 cm is never below P2');
if (depth !== null && depth >= 50) raiseTo('P2', 'Depth 50-100 cm');
if (kw.deep) raiseTo('P1', 'Caller reports water above car / chest level');
if (trapped && vulnerable) raiseTo('P1', 'Trapped vulnerable person');
if (vision && vision.moving_water === true && num(vision.people_visible) > 0) raiseTo('P1', 'People visible in moving water');

// 5. Escalation to a human operator
const conflict = t.conflict_detected === true || (vDepth !== null && vDepth < 20 && ((aDepth !== null && aDepth >= 50) || trapped));
let escalate = t.escalate_to_human === true || conflict;
if (conflict) notes.push('Vision and words conflict');
if (kwMissed.length) escalate = true;
if (!vision && !audio) { escalate = true; notes.push('No specialist result available'); }
if (vision && vision.confidence === 'low') { escalate = true; notes.push('Low-confidence vision estimate'); }
if (vision && vision.is_flood === false) { escalate = true; notes.push('Image does not look like a flood'); }
if (audio && !audio.is_genuine_emergency) { escalate = true; notes.push('Message may not be a genuine emergency'); }
if (audio && audio.transcription_failed) { escalate = true; notes.push('Voice note could not be transcribed'); }
if (!draftPriority) escalate = true;

// 6. Rescue asset must match the final tier (execution #49: a P2 truck on a 145 cm P1 photo)
const assetTier = (a) => {
  const s = String(a || '').toLowerCase();
  if (/zodiac|boat|bateau|helicop|airlift/.test(s)) return 'P1';
  if (/4x4|high-clearance|tactical/.test(s)) return 'P2';
  if (/tow|barricade|road closure/.test(s)) return 'P3';
  if (/patrol|drone|monitor/.test(s)) return 'P4';
  return null;
};
const expectedAsset = priority === 'P1' && trapped && vulnerable ? ASSET_P1_VULNERABLE : ASSET[priority];
const rescueAsset = t.rescue_asset && assetTier(t.rescue_asset) === priority ? t.rescue_asset : expectedAsset;
if (t.rescue_asset && rescueAsset !== t.rescue_asset) notes.push('Rescue asset "' + t.rescue_asset + '" does not match ' + priority + ': replaced');

const victimCount = audio && audio.victim_count !== null ? audio.victim_count : num(t.victim_count);
const depthConfidence = vDepth !== null ? vision.confidence : aDepth !== null ? 'reported' : 'none';
const reportCount = num(inp.report_count) || 1;

// 7. Ticket text in the citizen's language (deterministic wording, HTML-escaped for Telegram HTML mode)
const LANG = ['fr', 'ar'].includes(String(inp.lang || '').toLowerCase()) ? String(inp.lang).toLowerCase() : 'en';
const L = {
  en: { title: 'CrisisLink Incident Ticket', upd: 'update #', P: LABEL, depth: 'Water depth', unknown: 'unknown', src: 'source', srcs: { vision: 'photo', audio: 'voice/text', both: 'photo + voice/text', none: 'none' }, conf: 'photo confidence', confs: { high: 'high', medium: 'medium', low: 'low' }, victims: 'Victims', trapped: 'Trapped', medical: 'Medical', yes: 'yes', no: 'no', asset: 'Rescue asset', review: 'Human review', req: '⚠️ REQUIRED', notreq: 'not required', loc: 'Location', summary: 'Summary', advice: 'Safety advice', notes: 'Safety check', assets: ASSET, assetV: ASSET_P1_VULNERABLE },
  fr: { title: "Fiche d'incident CrisisLink", upd: 'mise à jour n°', P: { P1: 'P1 - Critique / Immédiat', P2: 'P2 - Élevé / Urgent', P3: 'P3 - Modéré / Secondaire', P4: 'P4 - Faible / Surveillance' }, depth: "Hauteur d'eau", unknown: 'inconnue', src: 'source', srcs: { vision: 'photo', audio: 'voix/texte', both: 'photo + voix/texte', none: 'aucune' }, conf: 'confiance photo', confs: { high: 'élevée', medium: 'moyenne', low: 'faible' }, victims: 'Victimes', trapped: 'Bloqués', medical: 'Médical', yes: 'oui', no: 'non', asset: 'Moyen de secours', review: 'Revue humaine', req: '⚠️ REQUISE', notreq: 'non requise', loc: 'Position', summary: 'Résumé', advice: 'Conseil de sécurité', notes: 'Contrôle de sécurité (pour le dispatcher, en anglais)',
    assets: { P1: 'Bateau pneumatique de sauvetage (Zodiac) / hélicoptère avec treuil', P2: 'Véhicule de secours 4x4 à grande garde au sol', P3: 'Dépanneuses / barrières de fermeture de route', P4: 'Patrouille / drone de surveillance' }, assetV: 'Bateau pneumatique de sauvetage (Zodiac) + équipe médicale' },
  ar: { title: 'بطاقة حادث CrisisLink', upd: 'تحديث رقم ', P: { P1: 'P1 - حرج / فوري', P2: 'P2 - عالٍ / عاجل', P3: 'P3 - متوسط / ثانوي', P4: 'P4 - منخفض / مراقبة' }, depth: 'عمق المياه', unknown: 'غير معروف', src: 'المصدر', srcs: { vision: 'صورة', audio: 'صوت/نص', both: 'صورة + صوت/نص', none: 'لا شيء' }, conf: 'ثقة الصورة', confs: { high: 'عالية', medium: 'متوسطة', low: 'منخفضة' }, victims: 'الضحايا', trapped: 'محاصرون', medical: 'حالة طبية', yes: 'نعم', no: 'لا', asset: 'وسيلة الإنقاذ', review: 'مراجعة بشرية', req: '⚠️ مطلوبة', notreq: 'غير مطلوبة', loc: 'الموقع', summary: 'الملخص', advice: 'نصيحة السلامة', notes: 'فحص السلامة (للمُرسِل، بالإنجليزية)',
    assets: { P1: 'قارب إنقاذ مطاطي (زودياك) / مروحية إنقاذ', P2: 'مركبة إنقاذ رباعية الدفع عالية الارتفاع', P3: 'سيارات سحب / حواجز إغلاق الطريق', P4: 'دورية / طائرة مراقبة' }, assetV: 'قارب إنقاذ مطاطي (زودياك) + فريق إسعاف' },
}[LANG];
const esc = (s) => String(s === null || s === undefined ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const shownAsset = LANG === 'en' ? rescueAsset : (priority === 'P1' && trapped && vulnerable ? L.assetV : L.assets[priority]);
const yn = (b) => (b ? L.yes : L.no);
const lines = [
  (reportCount > 1 ? '🔄 <b>' + L.title + ' - ' + L.upd + reportCount + '</b>' : '🚨 <b>' + L.title + '</b>'),
  EMOJI[priority] + ' <b>' + L.P[priority] + '</b>',
  '',
  '<b>' + L.depth + ':</b> ' + (depth === null ? L.unknown : depth + ' cm') + ' (' + L.src + ': ' + L.srcs[depthSource] + (vDepth !== null ? ', ' + L.conf + ': ' + (L.confs[vision.confidence] || vision.confidence) : '') + ')',
  '<b>' + L.victims + ':</b> ' + (victimCount === null ? L.unknown : victimCount) + ' | <b>' + L.trapped + ':</b> ' + yn(trapped) + ' | <b>' + L.medical + ':</b> ' + yn(medical),
  '<b>' + L.asset + ':</b> ' + esc(shownAsset),
  '<b>' + L.review + ':</b> ' + (escalate ? L.req : L.notreq),
];
if (inp.maps_link) lines.push('<b>' + L.loc + ':</b> ' + esc(inp.maps_link));
if (t.situation_summary) lines.push('', '<b>' + L.summary + ':</b> ' + esc(t.situation_summary));
if (t.citizen_safety_advice) lines.push('<b>' + L.advice + ':</b> ' + esc(t.citizen_safety_advice));
if (notes.length) lines.push('', '<i>' + L.notes + ': ' + esc(notes.join('; ')) + '</i>');

return JSON.stringify({
  priority,
  priority_color: COLOR[priority],
  draft_priority: draftPriority,
  depth_cm: depth,
  depth_source: depthSource,
  depth_confidence: depthConfidence,
  victim_count: victimCount,
  trapped,
  medical_flag: medical,
  rescue_asset: rescueAsset,
  escalate_to_human: escalate,
  guardrail_notes: notes.join('; '),
  followup_asked: !!(audio && audio.followup_asked),
  transcript: audio ? audio.transcript : '',
  asr_engine: audio ? audio.asr_engine : '',
  visual_cues: vision && Array.isArray(vision.visual_cues) ? vision.visual_cues.join(', ') : '',
  merged_vision_json: vision ? JSON.stringify(vision) : '',
  merged_distress_json: audio ? JSON.stringify(audio) : '',
  ticket_text: lines.join('\n'),
});
