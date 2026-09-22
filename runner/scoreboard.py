#!/usr/bin/env python3
"""Render a static scoreboard (HTML) from one or more results.json files.

Usage: python scoreboard.py results.json [other.json] --out scoreboard/index.html
With two files the second is compared case by case: the knowledge-layer
ablation when the two arms differ in `bundle`, and a runtime comparison
when they differ in `runtime` (the same capability release, the same
cases and graders, another runtime). The header states what each file
recorded: capability and version, release lock, runtime, model, date.
"""
import argparse
import json
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def mismatched_rubrics(on, off):
    """Cases the two arms did not grade by the same text.

    The pre-registration commits to grading trap-hit by the same rubric per
    case in both arms. A delta between a case graded one way and the same case
    graded another is a difference in the grader, and nothing renders it.
    """
    off_by_id = {c["id"]: c for c in off["cases"]}
    return [c["id"] for c in on["cases"]
            if c["id"] in off_by_id and c.get("rubric") != off_by_id[c["id"]].get("rubric")]


def rows(on, off=None):
    off_by_id = {c["id"]: c for c in off["cases"]} if off else {}
    for c in on["cases"]:
        o = off_by_id.get(c["id"])
        delta = None if o is None else round(c["rate"] - o["rate"], 3)
        yield c, o, delta


def label(r):
    """One line saying what a results file recorded."""
    rt = r.get("runtime") or {}
    caps = r.get("capabilities") or {}
    parts = []
    for name, c in sorted(caps.items()):
        lock = (c.get("release_lock") or "no lock")[:19]
        stale = "" if c.get("release_lock_current") in (True, None) else " (lock stale)"
        parts.append(f"{name} {c.get('version') or '?'} {lock}{stale}")
    return " | ".join(filter(None, [
        ", ".join(parts), rt.get("name") and f"runtime {rt['name']} ({rt.get('projection')}, {rt.get('version') or 'version unknown'})",
        f"model {r.get('model', '?')}", r.get("judge_model") and f"judge {r['judge_model']}",
        r.get("date") and f"date {r['date']}", f"N={r.get('trials', '?')}"]))


def comparison(on, off):
    """What the second file is: an ablation arm or another runtime."""
    if off is None:
        return None
    a = (on.get("runtime") or {}).get("name")
    b = (off.get("runtime") or {}).get("name")
    if a and b and a != b:
        return ("runtime", a, b)
    return ("bundle", f"bundle {on.get('bundle', 'on')}", f"bundle {off.get('bundle', 'off')}")


def outages(on, off=None):
    """Trials each arm lost, per case and in total.

    A lost trial is an outage and never enters a rate, which is right and is
    not the end of it. Consulting the bundle costs turns, because the skill
    reads concepts and each read is a turn, so the arm holding the knowledge
    exhausts its budget more readily and the trials that survive it are the
    atypically brief ones. That is a bias in the sample rather than in the
    rate, so no interval shows it. A shard probe on 2026-09-21 lost one of two
    bundle-on trials to the turn limit at a budget of 30, which is why this is
    reported beside the delta rather than left in the results file.
    """
    off_by_id = {c["id"]: c for c in off["cases"]} if off else {}
    per_case = []
    for c in on["cases"]:
        o = off_by_id.get(c["id"])
        per_case.append((c["id"], c.get("errors", 0), c.get("trials_requested", 0),
                         o.get("errors", 0) if o else None,
                         o.get("trials_requested", 0) if o else None))
    return per_case


def outage_rate(cases):
    lost = sum(c.get("errors", 0) for c in cases)
    asked = sum(c.get("trials_requested", 0) for c in cases)
    return lost, asked, (round(lost / asked, 3) if asked else 0.0)


def outage_block(on, off=None):
    """The outage paragraph and table that go under the delta."""
    a_lost, a_asked, a_rate = outage_rate(on["cases"])
    if off is None:
        if not a_lost:
            return ""
        return (f"<p><b>Outages:</b> {a_lost} of {a_asked} trials were lost and are not "
                "in any rate above.</p>")
    b_lost, b_asked, b_rate = outage_rate(off["cases"])
    gap = round(a_rate - b_rate, 3)
    warn = ("" if abs(gap) < 0.1 else
            " <b>The arms did not lose trials at the same rate.</b> A pooled risk "
            "difference across arms whose samples were thinned unequally is not read "
            "as a treatment effect without saying so.")
    rows_html = "".join(
        f"<tr><td>{cid}</td><td>{ae}/{aa}</td><td>{be}/{ba}</td></tr>"
        for cid, ae, aa, be, ba in outages(on, off) if be is not None)
    return (f"<h2>Outages</h2><p>Lost trials are not failures and are in no rate above. "
            f"They are reported because they do not fall evenly: consulting the bundle "
            f"costs turns, so the arm holding the knowledge exhausts its budget more "
            f"readily and its surviving trials are the atypically brief ones. "
            f"{on.get('bundle', 'on')} lost {a_lost} of {a_asked} ({a_rate}); "
            f"{off.get('bundle', 'off')} lost {b_lost} of {b_asked} ({b_rate}); "
            f"difference {'+' if gap >= 0 else ''}{gap}.{warn}</p>"
            f"<table><tr><th>case</th><th>{on.get('bundle','on')} lost</th>"
            f"<th>{off.get('bundle','off')} lost</th></tr>{rows_html}</table>")


def render(on, off=None):
    if off is not None:
        differ = mismatched_rubrics(on, off)
        if differ:
            raise SystemExit("these arms did not grade the same cases by the same "
                             "rubric, so their delta is a difference in the grader: "
                             + ", ".join(differ))
    kind = comparison(on, off)
    col_a = f"{kind[1]}: rate (95% CI)" if kind else "rate (95% CI)"
    head = (f"<tr><th>case</th><th>type</th><th>{col_a}</th>"
            + (f"<th>{kind[2]}: rate</th><th>delta</th>" if off else "")
            + "<th>verdict</th></tr>")
    body = []
    for c, o, delta in rows(on, off):
        cells = [f"<td>{c['id']}</td><td>{c.get('type','')}</td>",
                 f"<td>{c['rate']:.2f} [{c['ci95'][0]:.2f}, {c['ci95'][1]:.2f}]</td>"]
        if off:
            cells.append(f"<td>{o['rate']:.2f}</td>" if o else "<td>-</td>")
            cells.append(f"<td>{'+' if (delta or 0) >= 0 else ''}{delta}</td>" if delta is not None else "<td>-</td>")
        cells.append(f"<td class='{'p' if c['pass'] else 'f'}'>{'PASS' if c['pass'] else 'FAIL'}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    title = f"OSP evals: {on['manifest']} ({on['model']}, N={on['trials']})"
    if kind and kind[0] == "runtime":
        title += f", {kind[1]} against {kind[2]}"
    record = f"<p><b>A:</b> {label(on)}</p>" + (f"<p><b>B:</b> {label(off)}</p>" if off else "")
    note = ("Bundle-off columns, when present, are the knowledge-layer ablation."
            if not kind or kind[0] == "bundle" else
            "The second column is the same capability release and the same cases on another "
            "runtime; the delta is the runtime's, not the science's.")
    return f"""<!doctype html><meta charset=utf-8><title>{title}</title>
<style>body{{font:14px system-ui;margin:2rem;max-width:60rem}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}}
th{{background:#f4f4f4}}.p{{color:#137333;font-weight:600}}.f{{color:#c5221f;font-weight:600}}
caption{{text-align:left;color:#555;padding-bottom:.5rem}}</style>
<h1>{title}</h1>
{record}
<p>A case passes when its point-estimate pass rate meets the threshold; the
Wilson 95% interval is reported beside it. {note}</p>
<table>{head}{''.join(body)}</table>
{outage_block(on, off)}
<p style=color:#888>Generated from results.json by scoreboard.py.</p>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("results_off", nargs="?")
    ap.add_argument("--out", default="scoreboard/index.html")
    args = ap.parse_args()
    on = load(args.results)
    off = load(args.results_off) if args.results_off else None
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render(on, off))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
