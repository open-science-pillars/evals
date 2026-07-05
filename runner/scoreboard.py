#!/usr/bin/env python3
"""Render a static scoreboard (HTML) from one or more results.json files.

Usage: python scoreboard.py results.json [results_off.json] --out scoreboard/index.html
When two files are given (bundle on and off), renders the ablation delta.
"""
import argparse
import json
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def rows(on, off=None):
    off_by_id = {c["id"]: c for c in off["cases"]} if off else {}
    for c in on["cases"]:
        o = off_by_id.get(c["id"])
        delta = None if o is None else round(c["rate"] - o["rate"], 3)
        yield c, o, delta


def render(on, off=None):
    head = ("<tr><th>case</th><th>type</th><th>bundle on: rate (95% CI)</th>"
            + ("<th>bundle off: rate</th><th>delta</th>" if off else "")
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
    return f"""<!doctype html><meta charset=utf-8><title>{title}</title>
<style>body{{font:14px system-ui;margin:2rem;max-width:60rem}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}}
th{{background:#f4f4f4}}.p{{color:#137333;font-weight:600}}.f{{color:#c5221f;font-weight:600}}
caption{{text-align:left;color:#555;padding-bottom:.5rem}}</style>
<h1>{title}</h1>
<p>A case passes when the lower bound of its Wilson 95% pass-rate interval
meets the threshold: the suite holds itself to the uncertainty rule the
plugins enforce. Bundle-off columns, when present, are the knowledge-layer
ablation.</p>
<table>{head}{''.join(body)}</table>
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
