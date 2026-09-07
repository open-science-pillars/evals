"""Rubric judge: grade one trial transcript against a rubric with an LLM.

Uses a headless `claude -p` call with a strict PASS/FAIL contract. The judge
is deliberately skeptical: partial compliance is a FAIL, and a plausible-but-
wrong answer is a FAIL, matching the eval cases' own notes.

A judge that did not answer is not a verdict. A timeout, a usage-limit
message or a reply the contract cannot be read out of returns grade ERROR,
which the runner counts as an infrastructure error rather than as a failed
trial: a judge outage that silently reads as FAIL would put a wrong rate in
the record, which is the one thing a measurement must not do.
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


ERROR_MARKERS = ("reached your", "usage limit", "rate limit", "credit balance",
                 "quota", "overloaded")


def judge_trial(rubric_text, transcript, model="claude-fable-5", timeout=180):
    """Grade one transcript. The model defaults to claude-fable-5 and the
    runner passes its own --model, so the judge and the trials cannot end up
    on different models by accident."""
    prompt = JUDGE_PROMPT.format(rubric=rubric_text, transcript=transcript[:20000])
    try:
        out = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--max-turns", "1"],
            capture_output=True, text=True, timeout=timeout,
        ).stdout
    except subprocess.TimeoutExpired:
        return {"grade": "ERROR", "reason": f"judge timed out after {timeout}s"}
    low = out.lower()
    if len(out.strip()) < 20 or any(m in low for m in ERROR_MARKERS):
        return {"grade": "ERROR", "reason": f"judge did not answer: {out.strip()[:200]}"}
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
    return {"grade": "ERROR", "reason": f"unparseable judge output: {out.strip()[:200]}"}
