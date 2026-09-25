"""Distress Extractor prompt evaluation: V2 vs V3 vs V4 on 8 transcripts.

Cases 1-3 and 5 are real transcripts from the team's tests (Whisper and Gemini outputs of
test_media/audio). None of the cases appears in the V3 few-shot examples.

Each case lists the fields that must come out right; a case passes when all of them do.
Usage: python eval/extractor_eval.py   (reads groq_api_key from .env)
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
# Evaluations burn the free-tier daily quota (vision: 200k tokens/day, ~2-3k per photo).
# Set groq_eval_api_key (e.g. a teammate's key) so they never starve the live demo key.
GROQ_KEY = (os.getenv("groq_eval_api_key") or os.getenv("groq_api_key", "")).strip()
MODEL = "openai/gpt-oss-120b"  # same as the n8n "Build Extraction Request" node

CASES = [
    {"id": "derja_whisper", "note": "real Whisper transcript of 01_distress_derja.mp3 (execution #50)",
     "text": "عسلامة الموصل فوق الكرابة في نهجنا فمامرة كبيرة معانا في الدار مانجمش تخرج عاونونا يرحم والديكو.",
     "expect": {"trapped": True, "vulnerable": True, "depth_at_least": 100, "genuine": True}},
    {"id": "derja_gemini", "note": "real Gemini 3.5 Transcribe transcript of 01_distress_derja.mp3",
     "text": "الماء وصل فوق الكرهبه في نهجنا فما مرا كبيره معنا في الدار ماجمتش تخرج عاونونا يرحم والديكم",
     "expect": {"trapped": True, "vulnerable": True, "depth_at_least": 100, "genuine": True}},
    {"id": "french_car", "note": "real transcript of 02_distress_french.mp3",
     "text": "Urgence s'il vous plaît, l'eau dépasse 80 cm, nous sommes bloqués dans la voiture au milieu du carrefour.",
     "expect": {"trapped": True, "vulnerable": False, "depth_at_least": 80, "genuine": True}},
    {"id": "arabizi_playbook", "note": "example sentence from the Team Playbook",
     "text": "L-mé wsol l-carrhba, famma mra kbiira m3ana, ma najmnech nokhrjou!",
     "expect": {"trapped": True, "vulnerable": True, "genuine": True}},
    {"id": "english_girls", "note": "real text message from execution #51",
     "text": "Please help me we are 2 girls stuck in a home and its flooding outside",
     "expect": {"trapped": True, "victims": 2, "genuine": True}},
    {"id": "prank", "note": "adversarial: joke message",
     "text": "hahaha just kidding, I'm testing the bot, there is no water here",
     "expect": {"trapped": False, "genuine": False}},
    {"id": "derja_baby_knee", "note": "sick baby, knee-level water, not stated as trapped",
     "text": "البيبي مريض والماء قاعد يطلع في الدار، وصل للركبة",
     "expect": {"trapped": False, "vulnerable": True, "depth_at_least": 50, "genuine": True}},
    {"id": "french_disabled", "note": "disabled father stuck upstairs",
     "text": "Mon père handicapé est coincé au premier étage, l'eau monte vite",
     "expect": {"trapped": True, "vulnerable": True, "genuine": True}},
]


def messages(version: str, transcript: str) -> list[dict]:
    wrap = lambda s: 'Transcript:\n"""\n' + s + '\n"""'
    msgs = [{"role": "system", "content": (ROOT / "prompts" / f"extractor_{version.lower()}.txt").read_text(encoding="utf-8")}]
    if version in ("V3", "V4"):
        for ex in json.loads((ROOT / "prompts" / f"extractor_{version.lower()}_fewshot.json").read_text(encoding="utf-8")):
            msgs += [{"role": "user", "content": wrap(ex["transcript"])}, {"role": "assistant", "content": json.dumps(ex["output"], ensure_ascii=False)}]
    return msgs + [{"role": "user", "content": wrap(transcript)}]


def extract(version: str, transcript: str) -> dict:
    body = {"model": MODEL, "temperature": 0.1, "max_completion_tokens": 1500,
            "response_format": {"type": "json_object"}, "messages": messages(version, transcript)}
    for attempt in range(4):
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers={"Authorization": "Bearer " + GROQ_KEY}, json=body, timeout=90)
        if r.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
    raise RuntimeError("rate limited")


def check(out: dict, expect: dict) -> dict:
    got = {
        "trapped": out.get("trapped") is True,
        "vulnerable": bool(out.get("vulnerable_persons")) or out.get("medical_flag") is True,
        "genuine": out.get("is_genuine_emergency") is not False,
        "victims": out.get("victim_count"),
        "depth": out.get("reported_depth_cm"),
    }
    res = {}
    for k, v in expect.items():
        if k == "depth_at_least":
            res[k] = isinstance(got["depth"], (int, float)) and got["depth"] >= v
        else:
            res[k] = got[k] == v
    return {"got": got, "checks": res}


def main():
    results, summary = [], {}
    for version in ("V2", "V3", "V4"):
        passed = fields_ok = fields = 0
        for case in CASES:
            out = extract(version, case["text"])
            c = check(out, case["expect"])
            ok = all(c["checks"].values())
            passed += ok
            fields_ok += sum(c["checks"].values())
            fields += len(c["checks"])
            results.append({"version": version, "id": case["id"], "pass": ok, **c})
            print(f"{version} {case['id']:18s} {'PASS' if ok else 'FAIL'} {c['checks']}")
            time.sleep(1.5)
        summary[version] = {"cases_passed": f"{passed}/{len(CASES)}", "field_accuracy": round(fields_ok / fields, 3)}

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "extractor_eval.json").write_text(json.dumps({"model": MODEL, "summary": summary, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["# Distress Extractor Evaluation", "", f"Model: `{MODEL}` (Groq). {len(CASES)} transcripts; none appear in the V3/V4 few-shot examples.", "",
          "| Prompt | Cases fully correct | Field accuracy |", "|---|---|---|"]
    md += [f"| {v} | {s['cases_passed']} | {s['field_accuracy']:.0%} |" for v, s in summary.items()]
    md += ["", "| Case | Source | V2 | V3 | V4 |", "|---|---|---|---|---|"]
    for case in CASES:
        r = {x["version"]: x for x in results if x["id"] == case["id"]}
        fmt = lambda x: "PASS" if x["pass"] else "FAIL (" + ", ".join(k for k, ok in x["checks"].items() if not ok) + ")"
        md.append(f"| {case['id']} | {case['note']} | {fmt(r['V2'])} | {fmt(r['V3'])} | {fmt(r['V4'])} |")
    (out_dir / "extractor_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
