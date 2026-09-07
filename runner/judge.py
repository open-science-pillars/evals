"""Rubric judge: grade one trial transcript against a rubric with an LLM.

Uses a headless `claude -p` call with a strict PASS/FAIL contract. The judge
is deliberately skeptical: partial compliance is a FAIL, and a plausible-but-
wrong answer is a FAIL, matching the eval cases' own notes.

A judge that did not answer is not a verdict. A timeout, a usage-limit
message or an empty reply returns grade ERROR, which the runner counts as an
infrastructure error rather than as a failed trial: a judge outage that
silently reads as FAIL would put a wrong rate in the record, which is the one
thing a measurement must not do.

A judge that DID answer is a verdict even when the envelope is damaged. A
reply truncated mid-sentence still carries its grade, and dropping it would
lose a real failure and inflate the rate: the opposite bias, and just as
wrong. So the grade is salvaged from a reply that plainly states one, with
whatever reason survived, and ERROR is reserved for replies that state no
grade at all.
"""
import json
import re
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

# A stated grade, in the contract's form or in a damaged version of it.
GRADE_RE = re.compile(r'"grade"\s*:\s*"(PASS|FAIL)"', re.I)
REASON_RE = re.compile(r'"reason"\s*:\s*"(.*?)(?:"\s*[,}]|$)', re.S)


def parse_judgement(out: str) -> dict:
    """The verdict in a judge's reply, or ERROR when it states none."""
    low = out.lower()
    if len(out.strip()) < 20 or any(m in low for m in ERROR_MARKERS):
        return {"grade": "ERROR", "reason": f"judge did not answer: {out.strip()[:200]}"}
    # Ambiguity first: a reply that states two different grades is not a
    # verdict whichever one is read last, so it is an error rather than a
    # coin toss.
    stated = {g.upper() for g in GRADE_RE.findall(out)}
    if len(stated) > 1:
        return {"grade": "ERROR",
                "reason": f"the judge stated more than one grade ({', '.join(sorted(stated))}): "
                          f"{out.strip()[:200]}"}
    # The contract's own form: one JSON object on one line.
    start = out.rfind("{")
    end = out.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            d = json.loads(out[start:end + 1])
            if d.get("grade") in ("PASS", "FAIL"):
                return d
        except json.JSONDecodeError:
            pass
    # A damaged envelope around a stated verdict is still a verdict: a reply
    # truncated mid-reason carries its grade, and discarding it would drop a
    # real failure. Only the first grade token counts, and a reply naming
    # both is ambiguous rather than salvageable.
    grades = GRADE_RE.findall(out)
    if grades:
        reason = ""
        m = REASON_RE.search(out)
        if m:
            reason = m.group(1).strip()
        return {"grade": grades[0].upper(),
                "reason": (reason or "no reason survived") + " [salvaged from a truncated judge reply]",
                "salvaged": True}
    return {"grade": "ERROR", "reason": f"judge stated no grade: {out.strip()[:200]}"}


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
    return parse_judgement(out)


