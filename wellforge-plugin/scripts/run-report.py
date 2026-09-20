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


# There is exactly ONE pricing table: config/model-pricing.yml. This script used to carry
# an embedded copy "kept in sync" by comment — both drifted years stale (opus 15/75, haiku
# 0.80/4.00) and nothing caught it, because a wrong cost estimate still prints a number.
# A duplicated constant with a sync comment is a drift trap; if the table can't be read we
# report no cost, which is honest, instead of a confident wrong one.
def load_pricing(path):
    if not path or not os.path.exists(path):
        print(f"note: pricing table not found at {path} — cost not estimated", file=sys.stderr)
        return None
    try:
        import yaml
    except ImportError:
        # stderr, never stdout — --json output must stay pure JSON
        print("note: pyyaml unavailable — cost not estimated (pip install pyyaml)", file=sys.stderr)
        return None
    try:
        return yaml.safe_load(open(path))
    except Exception as e:  # noqa: BLE001
        print(f"note: pricing table unreadable ({e}) — cost not estimated", file=sys.stderr)
        return None


def price_for(model, pricing):
    """Longest key first, so `claude-sonnet-5` beats `sonnet` — the generations differ."""
    if not pricing:
        return None, False
    models = pricing.get("models", {})
    m = (model or "").lower()
    for key in sorted(models, key=len, reverse=True):
        if key.lower() in m:
            return models[key], True
    return pricing.get("default"), False


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


def _in_window(e, run):
    started, finished = run.get("started", ""), run.get("finished", "")
    ts = e.get("ts", "")
    if not (started and finished):
        return False
    return started <= ts <= finished


def _agents_of(run):
    return {(a.get("agent") or "").lower() for a in run.get("agents", []) if a.get("agent")}


def attribute(events, runs):
    """Assign each token event to at most ONE run. Returns {run_id: [events]}, plus the
    events that could not be attributed.

    Time alone is not an attribution key. Two runs execute concurrently on every parallel
    batch `/wellforge:implement` dispatches, their [started, finished] windows overlap, and
    a per-run window sum then counts *both* runs' tokens in *each* run's total — inflating
    both, silently, exactly when a run is most expensive.

    So: window first, then `agent_type` (recorded by the SubagentStop hook where the harness
    exposes it) to break a tie. An event whose window matches several runs and whose agent
    matches none of them, or more than one, is left UNATTRIBUTED and reported separately.
    An honest gap beats a number that is wrong in the direction of looking cheap.
    """
    by_run = {r.get("run_id"): [] for r in runs}
    unattributed = []
    for e in events:
        cands = [r for r in runs if _in_window(e, r)]
        if not cands:
            unattributed.append(e)
            continue
        if len(cands) > 1:
            at = (e.get("agent_type") or "").lower()
            if at:
                narrowed = [r for r in cands if at in _agents_of(r)]
                if len(narrowed) == 1:
                    cands = narrowed
        if len(cands) == 1:
            by_run[cands[0].get("run_id")].append(e)
        else:
            unattributed.append(e)
    return by_run, unattributed


def totals(evts, pricing):
    """Sum an already-attributed list of events → (in, out, cost|None, n, exact_rates)."""
    tok_in = tok_out = 0
    cost = 0.0
    all_exact = True
    for e in evts:
        ti = e.get("input_tokens") or 0
        to = e.get("output_tokens") or 0
        tok_in += ti
        tok_out += to
        rate, exact = price_for(e.get("model"), pricing)
        all_exact = all_exact and exact
        if rate and pricing:
            unit = pricing.get("unit_tokens", 1_000_000)
            cost += ti / unit * rate["input"] + to / unit * rate["output"]
    return tok_in, tok_out, (round(cost, 4) if pricing else None), len(evts), all_exact


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

    # Attribute once, over ALL runs (not just the filtered view) — a run excluded by
    # --feature still competes for an event, and ignoring it would re-create the
    # double-count the attribution exists to prevent.
    attributed, unattributed = attribute(events, all_runs)

    report = []
    for r in runs:
        ti, to, cost, n, exact = totals(attributed.get(r.get("run_id"), []), pricing)
        drift_open = [d for d in r.get("drift_events", []) if not d.get("resolved")]
        entry = {
            "run_id": r.get("run_id"), "command": r.get("command"), "feature": r.get("feature"),
            "rigor": r.get("rigor"), "rigor_recorded": r.get("rigor_recorded"),
            "result": r.get("result"), "agents": [a.get("agent") for a in r.get("agents", [])],
            "verdicts": r.get("verdicts", {}), "drift_open": len(drift_open),
            "input_tokens": ti, "output_tokens": to, "est_cost_usd": cost, "events": n,
            "cost_rates_exact": exact,
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
                _, c_to, _, _, _ = totals(attributed.get(control.get("run_id"), []), pricing)
                if c_to > 0:
                    entry["control_run_id"] = control.get("run_id")
                    entry["output_tokens_saved"] = c_to - to
                    entry["pct_saved"] = round((c_to - to) / c_to * 100, 1)

        report.append(entry)

    if args.json:
        print(json.dumps({"runs": report,
                          "unattributed_events": len(unattributed),
                          "cost_estimated": pricing is not None}, indent=2))
        return 0

    for x in report:
        toks = f"{x['input_tokens']}/{x['output_tokens']} tok (partial)" if x["events"] else "no token data"
        v = " ".join(f"{k}={vv}" for k, vv in x["verdicts"].items()) or "-"
        drift = f" ⚠{x['drift_open']} open drift" if x["drift_open"] else ""
        # A run that executed BELOW the feature's recorded tier produced less verification
        # than the spec's standard. Surfacing it is the point of recording it.
        rec = x.get("rigor_recorded")
        downgrade = (f"  ⚠ ran at {x['rigor']} — feature is recorded {rec}"
                     if rec and rec != x.get("rigor") else "")
        print(f"{x['run_id']}")
        print(f"    {x['command']} · {x['result']} · agents: {', '.join(x['agents'])}")
        print(f"    verdicts: {v} · {toks}{drift}")
        if downgrade:
            print(downgrade)
        if "output_tokens_saved" in x:
            print(
                f"    terse: saved ~{x['output_tokens_saved']} output tok "
                f"(~{x['pct_saved']}%) vs control {x['control_run_id']} (subagent output only)"
            )
    if unattributed:
        print(f"\n⚠ {len(unattributed)} token event(s) could not be attributed to a single run")
        print("  (overlapping run windows and no distinguishing agent_type). They are counted")
        print("  in NO run's total rather than in several — see the observability skill.")
    if pricing is None:
        print("\nCost not estimated: config/model-pricing.yml unreadable (see note above).")
    elif any(not x.get("cost_rates_exact", True) for x in report):
        print("\nSome runs used the DEFAULT rate — their model id matched no pricing key.")
    print(f"\n{len(report)} runs. Trajectory/verdicts/drift above are exact.")
    print("Tokens are PARTIAL — captured from subagent stops only; the main orchestrating")
    print("loop and cache tokens (which dominate cost) are NOT visible to WellForge.")
    print("For real session cost run  /usage  (Claude Code), not these numbers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
