#!/usr/bin/env python3
"""Regression matrix for run-report.py cost attribution.

The bug this exists for: events were summed by TIME WINDOW alone, so two runs executing in
parallel — the shape every `/wellforge:implement` batch of >=2 produces — each counted the
other's tokens. Both runs reported inflated totals and the estimated spend roughly doubled,
silently. Case 1 is that bug; it fails against the pre-fix script.

Run: wellforge-plugin/scripts/tests/run-report.test.py   (needs pyyaml)
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rr", os.path.join(HERE, "..", "run-report.py"))
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

PRICING = rr.load_pricing(os.path.join(HERE, "..", "..", "config", "model-pricing.yml"))
passed = failed = 0


def check(desc, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {desc}\n        want {want}\n        got  {got}")


def run(rid, agent, started, finished, schema="wellforge-run/v2", **extra):
    r = {"schema": schema, "run_id": rid, "started": started,
         "finished": finished, "agents": [{"agent": agent}]}
    r.update(extra)
    return r


def ev(ts, tin, tout, agent_type=None, model="claude-sonnet-5"):
    e = {"ts": ts, "model": model, "input_tokens": tin, "output_tokens": tout}
    if agent_type:
        e["agent_type"] = agent_type
    return e


print("run-report attribution matrix")

# 1. Parallel runs, overlapping windows, agent identity present → no double-count.
runs = [run("be", "backend-dev", "10:00", "10:10"), run("fe", "frontend-dev", "10:01", "10:09")]
events = [ev("10:05", 1000, 2000, "backend-dev"), ev("10:06", 500, 700, "frontend-dev")]
by_run, un = rr.attribute(events, runs)
check("parallel runs split by agent_type", [len(by_run["be"]), len(by_run["fe"]), len(un)], [1, 1, 0])
check("backend totals", rr.totals(by_run["be"], PRICING)[:2], (1000, 2000))
check("frontend totals", rr.totals(by_run["fe"], PRICING)[:2], (500, 700))

# 2. Same, WITHOUT identity (older harness) → unattributed, never counted twice.
by_run, un = rr.attribute([ev("10:05", 1000, 2000), ev("10:06", 500, 700)], runs)
check("ambiguous events are dropped, not duplicated",
      [len(by_run["be"]), len(by_run["fe"]), len(un)], [0, 0, 2])

# 3. Sequential runs need no identity — one window matches, so attribution still works.
seq = [run("a", "backend-dev", "10:00", "10:05"), run("b", "backend-dev", "10:06", "10:10")]
by_run, un = rr.attribute([ev("10:02", 10, 20), ev("10:08", 30, 40)], seq)
check("sequential runs attribute without agent_type",
      [len(by_run["a"]), len(by_run["b"]), len(un)], [1, 1, 0])

# 4. An event outside every window is unattributed, not folded into the nearest run.
by_run, un = rr.attribute([ev("23:59", 5, 5)], seq)
check("out-of-window event is unattributed", len(un), 1)

# 5. Pricing: the specific model id must win over the family name.
check("sonnet 5 rate", rr.price_for("claude-sonnet-5", PRICING)[0], {"input": 2.00, "output": 10.00})
check("sonnet 4.6 rate", rr.price_for("claude-sonnet-4-6", PRICING)[0], {"input": 3.00, "output": 15.00})
check("opus 5 rate", rr.price_for("claude-opus-5", PRICING)[0], {"input": 5.00, "output": 25.00})
check("haiku 4.5 rate", rr.price_for("claude-haiku-4-5", PRICING)[0], {"input": 1.00, "output": 5.00})
check("fable rate", rr.price_for("claude-fable-5-1", PRICING)[0], {"input": 10.00, "output": 50.00})

# 6. Stale prices must not come back (the drift this fix was reported for).
check("opus is not the retired 15/75", rr.price_for("claude-opus-5", PRICING)[0]["input"], 5.00)
check("haiku is not the retired 0.80", rr.price_for("claude-haiku-4-5", PRICING)[0]["input"], 1.00)

# 7. Unknown model → default rate, flagged as not exact.
rate, exact = rr.price_for("some-other-model", PRICING)
check("unknown model uses default, flagged inexact", [rate, exact], [PRICING["default"], False])

# 8. No pricing table → no cost, rather than a guessed one.
check("missing table yields no cost", rr.totals([ev("10:05", 100, 100)], None)[2], None)

# 8b. A --mode downgrade must be legible: rigor_recorded different from rigor is surfaced,
#     and identical/absent is silent. Recording it without surfacing it helps nobody.
src_rr = open(os.path.join(HERE, "..", "run-report.py")).read()
check("report entry carries rigor and rigor_recorded",
      '"rigor": r.get("rigor"), "rigor_recorded": r.get("rigor_recorded")' in src_rr, True)
check("downgrade is only flagged when the tiers differ",
      'rec and rec != x.get("rigor")' in src_rr, True)

# 8c. BOTH trace schemas are read. v2 added plugin_version; v1 traces predate it and must
#     still load — a reader that drops old traces on a schema bump turns the archive it
#     exists to preserve into a silent gap.
# An exact list on purpose: a new schema version must be added here deliberately, which is
# the moment to ask whether the old ones still load. They must.
check("v1, v2 and v3 are all accepted", sorted(rr.ACCEPTED_SCHEMAS),
      ["wellforge-run/v1", "wellforge-run/v2", "wellforge-run/v3"])
import tempfile as _tf, os as _os, json as _json
_d = _tf.mkdtemp(); _os.makedirs(_os.path.join(_d, "runs"))
for _rid, _schema in (("old", "wellforge-run/v1"), ("new", "wellforge-run/v2")):
    _r = run(_rid, "backend-dev", "2026-09-01T10:00:00Z", "2026-09-01T10:05:00Z", schema=_schema)
    if _schema.endswith("v2"):
        _r["plugin_version"] = "2.39.0"
    _json.dump(_r, open(_os.path.join(_d, "runs", _rid + ".json"), "w"))
_loaded = rr.load_runs(_os.path.join(_d, "runs"), "")
check("a v1 and a v2 trace both load", sorted(r["run_id"] for r in _loaded), ["new", "old"])
check("an unknown schema is still filtered out",
      len(rr.load_runs(_os.path.join(_d, "runs"), "")) , 2)
_json.dump({"schema": "wellforge-run/v99", "run_id": "future"},
           open(_os.path.join(_d, "runs", "future.json"), "w"))
check("an unrecognised schema is skipped, not crashed",
      sorted(r["run_id"] for r in rr.load_runs(_os.path.join(_d, "runs"), "")), ["new", "old"])

# ── budgets and rework (advisory signals, added 2026-09-20) ────────────────────
BUDGETS = rr.load_budgets()
check("budgets load", BUDGETS is not None, True)
check("budgets are advisory_only", BUDGETS["advisory_only"], True)
check("all three tiers have a feature ceiling",
      sorted(BUDGETS["tiers"]), ["mvp", "production", "spike"])

def _mkrun(rid, feature, tier, verdicts, agents):
    return {"schema": "wellforge-run/v3", "run_id": rid, "feature": feature, "rigor": tier,
            "started": "2026-09-01T10:00:00Z", "finished": "2026-09-01T10:30:00Z",
            "agents": [{"agent": a} for a in agents], "verdicts": verdicts, "drift_events": []}

# rework: a FAIL round is counted, a PASS round is not, and repeats inside one run count.
_runs = [
    _mkrun("r1", "001-x", "production", {"qe": "FAIL"}, ["backend-dev", "quality-engineer"]),
    _mkrun("r2", "001-x", "production", {"qe": "PASS"}, ["backend-dev", "quality-engineer"]),
    _mkrun("r3", "001-x", "production", {"security": "FAIL"}, ["backend-dev"]),
    _mkrun("r4", "002-y", "mvp", {"qe": "PASS"}, ["frontend-dev", "frontend-dev"]),
]
rw = rr.rework(_runs)
check("rework counts a qe FAIL round", rw["by_feature"]["001-x"]["rounds"], 2)
check("...attributing it to the agents in that run", rw["by_agent"]["backend-dev"], 2)
check("a security FAIL is also a rework round",
      rw["by_feature"]["001-x"]["agents"]["backend-dev"], 2)
check("a passing feature has no rounds", rw["by_feature"]["002-y"]["rounds"], 0)
check("a repeat dispatch inside one run is counted separately",
      rw["repeat_dispatches"]["frontend-dev"], 1)
check("a single dispatch is not a repeat", "backend-dev" in rw["repeat_dispatches"], False)

# budget states: over / within / unknown — and unknown is NOT within.
_report_over = [{"run_id": "r1", "feature": "001-x", "rigor": "production",
                 "est_cost_usd": 20.0, "events": 3, "agents": []}]
b = rr.budget_report(_report_over, _runs, BUDGETS)
check("spend above the tier ceiling is `over`", b["per_feature"][0]["state"], "over")
check("...with a percentage", b["per_feature"][0]["pct"], 167)
_report_within = [{"run_id": "r1", "feature": "001-x", "rigor": "production",
                   "est_cost_usd": 2.0, "events": 3, "agents": []}]
check("spend below the ceiling is `within`",
      rr.budget_report(_report_within, _runs, BUDGETS)["per_feature"][0]["state"], "within")
_report_nodata = [{"run_id": "r1", "feature": "001-x", "rigor": "production",
                   "est_cost_usd": 0.0, "events": 0, "agents": []}]
b0 = rr.budget_report(_report_nodata, _runs, BUDGETS)
check("NO token data is `unknown`, never `within`", b0["per_feature"][0]["state"], "unknown")
check("...and carries no misleading percentage", b0["per_feature"][0]["pct"], None)
check("a missing budgets file yields no report rather than a crash",
      rr.budget_report(_report_within, _runs, None), None)

# the tier ceiling actually used is the run's own tier
_mvp = [{"run_id": "r4", "feature": "002-y", "rigor": "mvp",
         "est_cost_usd": 5.0, "events": 2, "agents": []}]
bm = rr.budget_report(_mvp, _runs, BUDGETS)
check("mvp is measured against the mvp ceiling", bm["per_feature"][0]["ceiling_usd"], 4.0)
check("...and 5.00 over a 4.00 ceiling is over", bm["per_feature"][0]["state"], "over")

# top consumer comes from attributed events, by OUTPUT tokens
_attr = {"r1": [{"agent_type": "backend-dev", "output_tokens": 9000},
                {"agent_type": "quality-engineer", "output_tokens": 500}]}
bt = rr.budget_report(_report_within, _runs, BUDGETS, _attr)
check("top consumer is the biggest output producer", bt["per_feature"][0]["top_agent"], "backend-dev")

# 9. There must be no second pricing table in the script.
src = open(os.path.join(HERE, "..", "run-report.py")).read()
check("no embedded fallback pricing table", "_FALLBACK_PRICING" in src, False)

print(f"\nrun-report: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
