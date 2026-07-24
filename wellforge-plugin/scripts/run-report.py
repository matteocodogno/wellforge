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
from datetime import datetime


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


def _parse_ts(ts):
    """Parse a 'date -u +%FT%TZ' timestamp → datetime, or None if unparseable/absent."""
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def find_control(run, all_runs):
    """Pair a terse run to its non-terse control (US-5 / AC-5.1 compute half).

    Pairing heuristic, in order:
    1. **Explicit `control_run_id`** on the terse run — if it resolves to a known run in
       `all_runs`, use it. This is the producer/author's own pairing and always wins.
    2. **Fallback — nearest-in-time same feature+command.** Among all OTHER runs that share
       this run's `feature` and `command` and are NOT themselves terse, pick the one whose
       `started` timestamp is closest (absolute delta) to this run's `started`. Rationale:
       runs of the same feature+command close together in time are the most comparable —
       they're most likely to cover the same rough task set / codebase state, so the
       output-token delta between them is attributable to terseness rather than to the
       work itself having grown or shrunk. Ties are broken by `run_id` (stable, deterministic).
       If the explicit id was set but does not resolve, we still fall back to this heuristic
       rather than silently reporting no pairing.

    Returns the control run dict, or None if no candidate exists either way.
    """
    control_id = run.get("control_run_id")
    if control_id:
        for cand in all_runs:
            if cand.get("run_id") == control_id:
                return cand
        # explicit id set but not found in this runs dir — fall through to the heuristic

    feature = run.get("feature")
    command = run.get("command")
    this_ts = _parse_ts(run.get("started"))

    candidates = [
        c for c in all_runs
        if c is not run
        and c.get("run_id") != run.get("run_id")
        and not c.get("terse", False)
        and c.get("feature") == feature
        and c.get("command") == command
    ]
    if not candidates:
        return None
    if this_ts is None:
        # No usable timestamp on the terse run itself — degrade to "most recent control"
        # (still deterministic: sorted by run_id, which is timestamp-prefixed).
        return sorted(candidates, key=lambda c: c.get("run_id", ""))[-1]

    def delta(cand):
        cand_ts = _parse_ts(cand.get("started"))
        if cand_ts is None:
            return float("inf")
        return abs((cand_ts - this_ts).total_seconds())

    candidates.sort(key=lambda c: (delta(c), c.get("run_id", "")))
    return candidates[0]


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

    # Pairing (control lookup) must search the FULL runs dir, not just the --feature-filtered
    # subset, so a control run is never missed because of an unrelated CLI filter.
    all_runs = runs if not args.feature else load_runs(args.runs_dir, "")

    report = []
    for r in runs:
        ti, to, cost, n = cost_in_window(events, r.get("started", ""), r.get("finished", ""), pricing)
        drift_open = [d for d in r.get("drift_events", []) if not d.get("resolved")]
        entry = {
            "run_id": r.get("run_id"), "command": r.get("command"), "feature": r.get("feature"),
            "result": r.get("result"), "agents": [a.get("agent") for a in r.get("agents", [])],
            "verdicts": r.get("verdicts", {}), "drift_open": len(drift_open),
            "input_tokens": ti, "output_tokens": to, "est_cost_usd": cost, "events": n,
            "terse": bool(r.get("terse", False)),
        }

        # US-5 / AC-5.1 (compute half): a terse run gets paired with a non-terse control and
        # the output-token delta is surfaced. Subagent output only (Risk R1) — never implies
        # main-loop coverage. Only emitted when a control resolves AND the control window has
        # a positive output-token total (dividing by a zero/undiscovered baseline is
        # meaningless, so we omit rather than emit a bogus/undefined pct).
        if entry["terse"]:
            control = find_control(r, all_runs)
            if control is not None:
                c_ti, c_to, _, c_n = cost_in_window(
                    events, control.get("started", ""), control.get("finished", ""), pricing
                )
                if c_to > 0:
                    entry["control_run_id"] = control.get("run_id")
                    entry["output_tokens_saved"] = c_to - to
                    entry["pct_saved"] = round((c_to - to) / c_to * 100, 1)

        report.append(entry)

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
        if "output_tokens_saved" in x:
            print(
                f"    terse: saved ~{x['output_tokens_saved']} output tok "
                f"(~{x['pct_saved']}%) vs control {x['control_run_id']} (subagent output only)"
            )
    print(f"\n{len(report)} runs. Trajectory/verdicts/drift above are exact.")
    print("Tokens are PARTIAL — captured from subagent stops only; the main orchestrating")
    print("loop and cache tokens (which dominate cost) are NOT visible to WellForge.")
    print("For real session cost run  /usage  (Claude Code), not these numbers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
