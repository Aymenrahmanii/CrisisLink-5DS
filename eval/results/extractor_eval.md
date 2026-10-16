# Distress Extractor Evaluation

Model: `openai/gpt-oss-120b` (Groq). 8 transcripts; none appear in the V3/V4 few-shot examples.

| Prompt | Cases fully correct | Field accuracy |
|---|---|---|
| V2 | 6/8 | 89% |
| V3 | 6/8 | 93% |
| V4 | 8/8 | 100% |

| Case | Source | V2 | V3 | V4 |
|---|---|---|---|---|
| derja_whisper | real Whisper transcript of 01_distress_derja.mp3 (execution #50) | FAIL (vulnerable, depth_at_least) | FAIL (vulnerable) | PASS |
| derja_gemini | real Gemini 3.5 Transcribe transcript of 01_distress_derja.mp3 | FAIL (depth_at_least) | PASS | PASS |
| french_car | real transcript of 02_distress_french.mp3 | PASS | FAIL (depth_at_least) | PASS |
| arabizi_playbook | example sentence from the Team Playbook | PASS | PASS | PASS |
| english_girls | real text message from execution #51 | PASS | PASS | PASS |
| prank | adversarial: joke message | PASS | PASS | PASS |
| derja_baby_knee | sick baby, knee-level water, not stated as trapped | PASS | PASS | PASS |
| french_disabled | disabled father stuck upstairs | PASS | PASS | PASS |
