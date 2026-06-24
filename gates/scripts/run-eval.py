#!/usr/bin/env python3
"""Headless LM-judge eval gate (opt-in CI).

Scores a feature against gates/configs/eval-rubric.yml using the Anthropic API and exits
non-zero if the verdict is FAIL (weighted total < pass_score, or any dimension < floor).

  run-eval.py --rubric gates/configs/eval-rubric.yml --spec-dir specs/001-x [--base origin/main]
              [--model claude-sonnet-4-6] [--judge-response fixture.json]

--judge-response FILE: skip the API call and score a pre-canned judge JSON (for testing
the gating logic offline). The judge JSON shape:
  {"scores": [{"key": "ac_satisfaction", "score": 5, "evidence": "..."}, ...]}

Needs ANTHROPIC_API_KEY (unless --judge-response). Costs tokens — wire it on agent-facing
or high-stakes changes, not every PR (see gates/README.md, "eval gate").

Model routing: the CI judge defaults to sonnet (automated, every gated PR — cost-conscious);
the in-session `evaluator` agent runs frontier (opus) since it's interactive and low-volume.
Pass --model opus for a stricter CI judge on high-stakes changes. (See plugin
config/model-routing.yml.)
"""
import argparse
import json
import os
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("run-eval.py needs pyyaml (CI runs it via `uv run --with pyyaml,anthropic`)")


def load_rubric(path):
    with open(path) as f:
        r = yaml.safe_load(f)
    by_key = {d["key"]: d for d in r["dimensions"]}
    return r, by_key


def gate(rubric, by_key, scores):
    """Pure scoring: returns (verdict, total, rows). No I/O — unit-testable."""
    scale = rubric["scale"]
    total = 0.0
    rows = []
    seen = {s["key"]: s for s in scores}
    failed_floor = []
    for key, dim in by_key.items():
        s = seen.get(key)
        score = int(s["score"]) if s else 1  # a missing dimension scores worst
        weighted = (score / scale) * dim["weight"]
        total += weighted
        below = score < dim["floor"]
        if below:
            failed_floor.append(key)
        rows.append((dim["title"], dim["weight"], score, dim["floor"], round(weighted, 1), below))
    total = round(total, 1)
    passed = total >= rubric["pass_score"] and not failed_floor
    return ("PASS" if passed else "FAIL"), total, rows, failed_floor


def gather(spec_dir, base):
    parts = []
    for name in ("spec.md", "plan.md", "tasks.md"):
        p = os.path.join(spec_dir, name)
        if os.path.exists(p):
            parts.append(f"===== {name} =====\n{open(p).read()}")
    if base:
        try:
            diff = subprocess.run(
                ["git", "diff", f"{base}...HEAD"], capture_output=True, text=True, timeout=60
            ).stdout
            if diff.strip():
                parts.append(f"===== git diff {base}...HEAD =====\n{diff[:60000]}")
        except Exception as e:  # noqa: BLE001
            parts.append(f"(diff unavailable: {e})")
    return "\n\n".join(parts)


def judge_via_api(rubric, materials, model):
    try:
        import anthropic
    except ImportError:
        sys.exit("run-eval.py needs the anthropic SDK for live judging (uv run --with anthropic)")
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    dims = "\n".join(
        f"- {d['key']} (1–{rubric['scale']}, floor {d['floor']}): {d['title']}. "
        f"Anchors: {d['anchors']}"
        for d in rubric["dimensions"]
    )
    prompt = (
        "You are an adversarial LM-judge scoring a software feature against a rubric. "
        "Default to the LOWER anchor when evidence is ambiguous; cite concrete evidence "
        "for every score. Return ONLY JSON: "
        '{\"scores\":[{\"key\":...,\"score\":int,\"evidence\":str}, ...]}.\n\n'
        f"RUBRIC DIMENSIONS:\n{dims}\n\nFEATURE MATERIALS:\n{materials}"
    )
    msg = client.messages.create(
        model=model, max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        sys.exit(f"judge returned no JSON:\n{text[:500]}")
    return json.loads(text[start:end + 1])["scores"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric", required=True)
    ap.add_argument("--spec-dir", required=True)
    ap.add_argument("--base", default="")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--judge-response", default="")
    args = ap.parse_args()

    rubric, by_key = load_rubric(args.rubric)
    if args.judge_response:
        scores = json.load(open(args.judge_response))["scores"]
    else:
        scores = judge_via_api(rubric, gather(args.spec_dir, args.base), args.model)

    verdict, total, rows, failed = gate(rubric, by_key, scores)
    print(f"Eval ({rubric['version']}) — {args.spec_dir}")
    print(f"{'dimension':32} {'score':>5} {'floor':>5} {'weighted':>9}")
    for title, _w, score, floor, weighted, below in rows:
        flag = "  ✗ below floor" if below else ""
        print(f"{title:32} {score:>5} {floor:>5} {weighted:>9}{flag}")
    print(f"{'TOTAL':32} {'':>5} {'':>5} {total:>9}/100  (pass ≥ {rubric['pass_score']})")
    if failed:
        print(f"::error::eval FAIL — dimensions below floor: {', '.join(failed)}")
    elif verdict == "FAIL":
        print(f"::error::eval FAIL — total {total} < pass_score {rubric['pass_score']}")
    print(f"verdict: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
