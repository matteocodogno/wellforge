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

# 9. There must be no second pricing table in the script.
src = open(os.path.join(HERE, "..", "run-report.py")).read()
check("no embedded fallback pricing table", "_FALLBACK_PRICING" in src, False)

print(f"\nrun-report: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
