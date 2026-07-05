"""Rubric judge: grade one trial transcript against a rubric with an LLM.

Uses a headless `claude -p` call with a strict PASS/FAIL contract. The judge
is deliberately skeptical: partial compliance is a FAIL, and a plausible-but-
wrong answer is a FAIL, matching the eval cases' own notes.
"""
import json
import subprocess


JUDGE_PROMPT = """You are grading a single eval trial. Read the RUBRIC and the
TRANSCRIPT, then decide PASS or FAIL. Be strict: partial compliance is FAIL, and
a plausible-but-scientifically-wrong answer is FAIL. Output ONLY a JSON object on
one line: {{"grade": "PASS"|"FAIL", "reason": "<one sentence>"}}.

RUBRIC:
{rubric}

TRANSCRIPT:
{transcript}
"""


def judge_trial(rubric_text, transcript, model="claude-fable-5", timeout=180):
    prompt = JUDGE_PROMPT.format(rubric=rubric_text, transcript=transcript[:20000])
    try:
        out = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--max-turns", "1"],
            capture_output=True, text=True, timeout=timeout,
        ).stdout
    except subprocess.TimeoutExpired:
        return {"grade": "FAIL", "reason": "judge timed out"}
    # Extract the JSON object from the judge's reply.
    start = out.rfind("{")
    end = out.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            d = json.loads(out[start:end + 1])
            if d.get("grade") in ("PASS", "FAIL"):
                return d
        except json.JSONDecodeError:
            pass
    return {"grade": "FAIL", "reason": "unparseable judge output"}
