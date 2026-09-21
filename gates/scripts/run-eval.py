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


def applies(dim, present):
    """Does a conditional dimension apply, given the artifacts actually on disk?

    `applies_when` reads like "design.md present"; the first token is the filename. A
    dimension with no `applies_when` always applies.

    This used to be decided by whether the JUDGE emitted a score, which inverts the
    control: a judge that forgot `design_fidelity` on a feature that HAS a design.md made
    the dimension disappear — 15% of the rubric silently dropped and the total
    re-normalised over what was left, so the run scored 100/100 and passed. Presence on
    disk is a fact; what the judge chose to return is the thing being graded.
    """
    cond = dim.get("applies_when")
    if not cond:
        return True
    if present is None:                       # caller did not say — fall back to old behaviour
        return None
    return cond.split()[0] in present


def gate(rubric, by_key, scores, present=None):
    """Pure scoring: returns (verdict, total, rows, failed_floor, errors). No I/O.

    `present` is the set of artifact filenames found in the spec dir (see gather_present).
    Conditional dimensions apply iff their artifact is present; an applicable dimension the
    judge did not score counts as worst (1), exactly like an always-on one. A dimension that
    does not apply is N/A — excluded from the total, which re-normalises over the dimensions
    that DO apply, and its floor does not bite.
    """
    scale = rubric["scale"]
    seen = {s["key"]: s for s in scores if isinstance(s, dict) and "key" in s}
    total_weighted = 0.0
    total_weight = 0.0
    rows = []
    failed_floor = []
    errors = []
    for key, dim in by_key.items():
        s = seen.get(key)
        applicable = applies(dim, present)
        if applicable is None:                # unknown: preserve the pre-existing behaviour
            applicable = s is not None
        if not applicable:
            if s is not None:
                errors.append(f"{key}: judge scored a dimension that does not apply "
                              f"({dim['applies_when']}) — ignored")
            rows.append((dim["title"], dim["weight"], None, dim["floor"], None, False))  # N/A
            continue
        raw = s["score"] if s else 1          # a missing applicable dimension scores worst
        try:
            score = int(raw)
        except (TypeError, ValueError):
            errors.append(f"{key}: score {raw!r} is not an integer")
            score = 1
        # CLAMP, and treat the excursion as a judge error. Unclamped, a judge returning 9 on
        # a 1-5 scale produced `TOTAL 180.0/100 ... PASS` — a verdict arithmetically incapable
        # of failing, printed with the same confidence as a real one. Clamping alone would
        # silently repair a judge that is not answering the question asked, so the run also
        # fails: a score outside the scale means the judge misread the rubric, and nothing
        # about the rest of its output has earned trust.
        if score < 1 or score > scale:
            errors.append(f"{key}: score {score} is outside the 1-{scale} scale")
            score = max(1, min(score, scale))
        weighted = (score / scale) * dim["weight"]
        total_weighted += weighted
        total_weight += dim["weight"]
        below = score < dim["floor"]
        if below:
            failed_floor.append(key)
        rows.append((dim["title"], dim["weight"], score, dim["floor"], round(weighted, 1), below))
    total = round((total_weighted / total_weight) * 100, 1) if total_weight else 0.0
    passed = total >= rubric["pass_score"] and not failed_floor and not errors
    return ("PASS" if passed else "FAIL"), total, rows, failed_floor, errors


ARTIFACTS = ("spec.md", "plan.md", "tasks.md", "design.md")


def gather_present(spec_dir):
    """Which rubric artifacts exist on disk. This is what decides whether a conditional
    dimension applies — not the judge's choice of what to score."""
    return {name for name in ARTIFACTS if os.path.exists(os.path.join(spec_dir, name))}


def gather(spec_dir, base):
    parts = []
    for name in ARTIFACTS:
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
        + (f"[CONDITIONAL — score ONLY if {d['applies_when']} appears in the materials; "
           "otherwise OMIT this key entirely] " if d.get("applies_when") else "")
        + f"Anchors: {d['anchors']}"
        for d in rubric["dimensions"]
    )
    prompt = (
        "You are an adversarial LM-judge scoring a software feature against a rubric. "
        "Default to the LOWER anchor when evidence is ambiguous; cite concrete evidence "
        "for every score. Omit any CONDITIONAL dimension whose condition isn't met by the "
        "materials (do not score it 1 — leave its key out). Return ONLY JSON: "
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

    # Presence on disk decides which conditional dimensions apply — see applies().
    verdict, total, rows, failed, errors = gate(rubric, by_key, scores,
                                                gather_present(args.spec_dir))
    print(f"Eval ({rubric['version']}) — {args.spec_dir}")
    print(f"{'dimension':32} {'score':>5} {'floor':>5} {'weighted':>9}")
    for title, _w, score, floor, weighted, below in rows:
        if score is None:
            print(f"{title:32} {'n/a':>5} {'—':>5} {'n/a':>9}  (not applicable)")
            continue
        flag = "  ✗ below floor" if below else ""
        print(f"{title:32} {score:>5} {floor:>5} {weighted:>9}{flag}")
    print(f"{'TOTAL':32} {'':>5} {'':>5} {total:>9}/100  (pass ≥ {rubric['pass_score']})")
    # Judge errors first: they explain why a total that looks passing is not one.
    for e in errors:
        print(f"::error::eval FAIL — judge error: {e}")
    if errors:
        print("::error::A score outside the rubric's scale means the judge misread the "
              "rubric; the run is failed rather than silently clamped into a pass.")
    if failed:
        print(f"::error::eval FAIL — dimensions below floor: {', '.join(failed)}")
    elif verdict == "FAIL" and not errors:
        print(f"::error::eval FAIL — total {total} < pass_score {rubric['pass_score']}")
    print(f"verdict: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
