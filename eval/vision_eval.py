"""Vision prompt evaluation on the labelled flood photos in test_media/.

Runs each prompt version (prompts/vision_v*.txt) through the same Groq vision model the
n8n workflow uses and scores the depth estimates against the folder / file-name labels.

Metrics per prompt version:
- in_range: estimate falls inside the labelled depth range
- error_cm: distance from the estimate to the labelled range (0 when inside), averaged
- underestimates: estimate below the range (the safety-critical direction)
- tier_accuracy: tier derived from the estimate (same thresholds as the Safety Guardrail) == labelled tier
- dangerous_misses: a P1 photo graded P3, P4 or with no depth at all

Usage: python eval/vision_eval.py   (reads groq_api_key from .env)
"""

import base64
import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
# Evaluations burn the free-tier daily quota (vision: 200k tokens/day, ~2-3k per photo).
# Set groq_eval_api_key (e.g. a teammate's key) so they never starve the live demo key.
GROQ_KEY = (os.getenv("groq_eval_api_key") or os.getenv("groq_api_key", "")).strip()

MODEL = "qwen/qwen3.8-27b"  # same as the n8n "Build Vision Request" node
PROMPTS = {"V1": ROOT / "prompts" / "vision_v1.txt", "V2": ROOT / "prompts" / "vision_v2.txt"}
SLEEP_S = 2.5  # stay under the free-tier requests-per-minute limit

# (glob, depth range in cm, expected tier)
LABELS = [
    ("test_media/imagess/10-15/*.jpg", (10, 15), "P4"),
    ("test_media/imagess/(Moderate  Car Wheels)depth 35–45 cm/*.jpg", (35, 45), "P3"),
    ("test_media/imagess/Photo 3 (Severe  Critical)  depth  100 cm/*.jpg", (100, 200), "P1"),
    ("test_media/images/01_shallow_ankle_15cm.jpg", (10, 20), "P4"),
    ("test_media/images/02_moderate_wheel_40cm.jpg", (35, 45), "P3"),
    ("test_media/images/03_severe_submerged_120cm.jpg", (110, 130), "P1"),
]


def tier(depth):
    """Same thresholds as the Safety Guardrail's depth fallback."""
    if depth is None:
        return None
    return "P1" if depth > 100 else "P2" if depth >= 50 else "P3" if depth >= 20 else "P4"


CACHE = ROOT / "eval" / "results" / "vision_cache.json"


def ask_cached(version: str, prompt: str, image: Path) -> dict:
    """Answers are cached per (prompt version, image) so an interrupted run resumes where it stopped."""
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    key = f"{version}|{image.relative_to(ROOT).as_posix()}"
    if key not in cache:
        answer = ask(prompt, image)
        if answer.get("_rate_limited"):
            return answer  # never cache a rate-limit failure as if it were the model's answer
        cache[key] = answer
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
        time.sleep(SLEEP_S)
    return cache[key]


def reset_seconds(value: str) -> float:
    """Groq reset headers look like '15.854s', '1m2.5s' or '850ms'."""
    if not value:
        return 15.0
    if value.endswith("ms"):
        return float(value[:-2]) / 1000
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", value)
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3) or 0)) if m else 15.0


def ask(prompt: str, image: Path) -> dict:
    body = {
        "model": MODEL,
        "temperature": 0.1,
        "max_completion_tokens": 1024,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": [
                {"type": "text", "text": "Citizen caption: (none)\nAnalyse this photo and return the JSON."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(image.read_bytes()).decode()}},
            ]},
        ],
    }
    # Free tier: 8,000 tokens/minute for this model and one photo request uses ~2-3k,
    # so wait for the token window Groq reports instead of guessing a backoff
    for attempt in range(12):
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers={"Authorization": "Bearer " + GROQ_KEY}, json=body, timeout=90)
        if r.status_code == 429:
            wait = max(reset_seconds(r.headers.get("x-ratelimit-reset-tokens", "")), float(r.headers.get("retry-after", 0) or 0)) + 1
            print(f"  rate limited, waiting {wait:.0f} s", flush=True)
            time.sleep(wait)
            continue
        r.raise_for_status()
        if int(r.headers.get("x-ratelimit-remaining-tokens", 8000)) < 3500:
            time.sleep(reset_seconds(r.headers.get("x-ratelimit-reset-tokens", "")) + 1)
        try:
            return json.loads(r.json()["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError):
            return {"_parse_error": True}
    return {"_parse_error": True, "_rate_limited": True}


def num(x):
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def main():
    images = [(p, rng, t) for pattern, rng, t in LABELS for p in sorted(ROOT.glob(pattern))]
    print(f"{len(images)} labelled images, model {MODEL}")
    rows, summary = [], {}

    for version, path in PROMPTS.items():
        prompt = path.read_text(encoding="utf-8")
        stats = {"n": 0, "parsed": 0, "estimated": 0, "in_range": 0, "under": 0, "tier_ok": 0, "danger": 0, "err": []}
        for img, (lo, hi), expected in images:
            out = ask_cached(version, prompt, img)
            d = None if out.get("is_flood") is False else num(out.get("estimated_depth_cm"))
            predicted = tier(d)
            stats["n"] += 1
            stats["parsed"] += 0 if out.get("_parse_error") else 1
            if d is not None:
                stats["estimated"] += 1
                stats["in_range"] += lo <= d <= hi
                stats["under"] += d < lo
                stats["err"].append(0 if lo <= d <= hi else (lo - d if d < lo else d - hi))
            stats["tier_ok"] += predicted == expected
            stats["danger"] += expected == "P1" and predicted in (None, "P3", "P4")
            rows.append({"version": version, "image": str(img.relative_to(ROOT)), "label_cm": f"{lo}-{hi}", "expected_tier": expected,
                         "estimated_cm": d, "predicted_tier": predicted, "confidence": out.get("confidence"),
                         "anchor": out.get("anchor"), "is_flood": out.get("is_flood")})
            print(f"{version} {expected} {lo:>3}-{hi:<3} -> {str(d):>6} {str(predicted):4s} {img.name}")
        n = stats["n"]
        summary[version] = {
            "images": n,
            "json_valid": round(stats["parsed"] / n, 3),
            "depth_given": round(stats["estimated"] / n, 3),
            "in_range": round(stats["in_range"] / n, 3),
            "mean_error_cm": round(sum(stats["err"]) / len(stats["err"]), 1) if stats["err"] else None,
            "underestimates": round(stats["under"] / n, 3),
            "tier_accuracy": round(stats["tier_ok"] / n, 3),
            "dangerous_misses": stats["danger"],
        }

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "vision_eval.json").write_text(json.dumps({"model": MODEL, "summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# Vision Depth Evaluation", "", f"Model: `{MODEL}` (Groq). {len(images)} labelled photos from `test_media/`. "
          "Tiers use the Safety Guardrail thresholds (P1 > 100 cm, P2 >= 50, P3 >= 20, P4 below).", "",
          "| Prompt | JSON valid | Depth given | In labelled range | Mean error (cm) | Underestimates | Tier accuracy | Dangerous misses (P1 graded P3/P4/none) |",
          "|---|---|---|---|---|---|---|---|"]
    for v, s in summary.items():
        md.append(f"| {v} | {s['json_valid']:.0%} | {s['depth_given']:.0%} | {s['in_range']:.0%} | {s['mean_error_cm']} | {s['underestimates']:.0%} | {s['tier_accuracy']:.0%} | {s['dangerous_misses']} |")
    md += ["", "## Per image", "", "| Prompt | Image | Label (cm) | Expected | Estimate (cm) | Predicted | Confidence | Anchor |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['version']} | {re.sub(r'^test_media/', '', r['image'])} | {r['label_cm']} | {r['expected_tier']} | {r['estimated_cm'] if r['estimated_cm'] is not None else '-'} | {r['predicted_tier'] or '-'} | {r['confidence'] or '-'} | {r['anchor'] or '-'} |")
    (out_dir / "vision_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
