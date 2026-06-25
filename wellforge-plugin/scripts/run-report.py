#!/usr/bin/env python3
"""WellForge run-report — summarize agent run traces (.forge/runs/) with cost estimates.

  run-report.py [--runs-dir .forge/runs] [--feature NNN-slug] [--pricing <model-pricing.yml>]
                [--json]

Reads the semantic run traces (wellforge-run/v1) the workflow commands write, joins the
best-effort token events (.events.jsonl) by each run's [started, finished] window, and
prints per-run agents/verdicts/drift + an estimated cost. Token/cost are ESTIMATES (see
skills/observability "Honest limits"); the who/what/verdict/drift parts are exact.

Pure-stdlib except pyyaml for pricing (optional — degrades to no cost if absent).
"""
import argparse
import glob
import json
import os
import sys


# Embedded fallback so cost ALWAYS computes — even without pyyaml or the config file.
# Keep in sync with config/model-pricing.yml (USD per 1M tokens).
_FALLBACK_PRICING = {
    "version": "fallback", "unit_tokens": 1000000,
    "models": {"opus": {"input": 15.0, "output": 75.0},
               "sonnet": {"input": 3.0, "output": 15.0},
               "haiku": {"input": 0.8, "output": 4.0}},
    "default": {"input": 3.0, "output": 15.0},
}


def load_pricing(path):
    if path and os.path.exists(path):
        try:
            import yaml
            return yaml.safe_load(open(path))
        except ImportError:
            # stderr, never stdout — --json output must stay pure JSON
            print("note: pyyaml unavailable — using built-in pricing fallback", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"note: pricing config unreadable ({e}) — using built-in fallback", file=sys.stderr)
    return _FALLBACK_PRICING


def price_for(model, pricing):
    if not pricing:
        return None
    models = pricing.get("models", {})
    m = (model or "").lower()
    for key, rate in models.items():
        if key in m:
            return rate
    return pricing.get("default")


def load_events(runs_dir):
    path = os.path.join(runs_dir, ".events.jsonl")
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def cost_in_window(events, started, finished, pricing):
    """Sum tokens of events within [started, finished] (string compare on ISO ts), → $."""
    tok_in = tok_out = 0
    cost = 0.0
    counted = 0
    for e in events:
        ts = e.get("ts", "")
        if started and finished and not (started <= ts <= finished):
            continue
        ti = e.get("input_tokens") or 0
        to = e.get("output_tokens") or 0
        tok_in += ti
        tok_out += to
        counted += 1
        rate = price_for(e.get("model"), pricing)
        if rate and pricing:
            unit = pricing.get("unit_tokens", 1_000_000)
            cost += ti / unit * rate["input"] + to / unit * rate["output"]
    return tok_in, tok_out, (round(cost, 4) if pricing else None), counted


def load_runs(runs_dir, feature):
    runs = []
    for fp in sorted(glob.glob(os.path.join(runs_dir, "*.json"))):
        try:
            r = json.load(open(fp))
        except json.JSONDecodeError:
            continue
        if r.get("schema") != "wellforge-run/v1":
            continue
        if feature and r.get("feature") != feature and feature not in r.get("feature", ""):
            continue
        runs.append(r)
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default=".forge/runs")
    ap.add_argument("--feature", default="")
    ap.add_argument("--pricing", default=os.path.join(os.path.dirname(__file__), "..", "config", "model-pricing.yml"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.runs_dir):
        print(f"no runs yet ({args.runs_dir} not found)")
        return 0

    pricing = load_pricing(args.pricing)
    events = load_events(args.runs_dir)
    runs = load_runs(args.runs_dir, args.feature)
    if not runs:
        print("no run traces found")
        return 0

    report = []
    for r in runs:
        ti, to, cost, n = cost_in_window(events, r.get("started", ""), r.get("finished", ""), pricing)
        drift_open = [d for d in r.get("drift_events", []) if not d.get("resolved")]
        report.append({
            "run_id": r.get("run_id"), "command": r.get("command"), "feature": r.get("feature"),
            "result": r.get("result"), "agents": [a.get("agent") for a in r.get("agents", [])],
            "verdicts": r.get("verdicts", {}), "drift_open": len(drift_open),
            "input_tokens": ti, "output_tokens": to, "est_cost_usd": cost, "events": n,
        })

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    for x in report:
        toks = f"{x['input_tokens']}/{x['output_tokens']} tok (partial)" if x["events"] else "no token data"
        v = " ".join(f"{k}={vv}" for k, vv in x["verdicts"].items()) or "-"
        drift = f" ⚠{x['drift_open']} open drift" if x["drift_open"] else ""
        print(f"{x['run_id']}")
        print(f"    {x['command']} · {x['result']} · agents: {', '.join(x['agents'])}")
        print(f"    verdicts: {v} · {toks}{drift}")
    print(f"\n{len(report)} runs. Trajectory/verdicts/drift above are exact.")
    print("Tokens are PARTIAL — captured from subagent stops only; the main orchestrating")
    print("loop and cache tokens (which dominate cost) are NOT visible to WellForge.")
    print("For real session cost run  /usage  (Claude Code), not these numbers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
