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

# 10. load_runs is the boundary where untrusted files become objects. Every consumer
#     (run-report, forge-state, and through it /status /triage /done /promote and the
#     post-spec-guard hook) used to inherit an AttributeError from one bad file.
import shutil as _sh
d = tempfile.mkdtemp()
cases = {
    "list.json":      "[1]",
    "string.json":    '"hello"',
    "null.json":      "null",
    "agents.json":    '{"schema":"wellforge-run/v3","feature":"f","agents":"x"}',
    "agentnull.json": '{"schema":"wellforge-run/v3","feature":"f","agents":[null]}',
    "verdicts.json":  '{"schema":"wellforge-run/v3","feature":"f","verdicts":"PASS"}',
    "schema.json":    '{"schema":"wellforge-run/v9","feature":"f"}',
    "trunc.json":     '{"schema":',
}
for name, body in cases.items():
    open(os.path.join(d, name), "w").write(body)
good = {"schema": "wellforge-run/v3", "run_id": "good", "feature": "f",
        "started": "2026-09-01T10:00:00Z", "finished": "2026-09-01T10:30:00Z",
        "agents": [{"agent": "backend-dev"}], "verdicts": {"qe": "PASS"}}
json.dump(good, open(os.path.join(d, "good.json"), "w"))

rejected = []
runs = rr.load_runs(d, "", rejected)
# Two different outcomes on purpose. A file that is not a trace at all (not an object, or
# an unknown schema, or unreadable) is DROPPED. A real trace with one malformed container
# field is KEPT with that field coerced, because dropping it would also discard the
# verdicts and timings sitting well-formed beside the bad field — and a discarded verdict
# reads downstream as "absent", which is how a passing gate turns into a refusal.
check("files that are not traces are dropped",
      sorted(r.get("run_id") for r in runs if r.get("run_id")), ["good"])
check("...and traces with one bad field are kept, coerced", len(runs), 4)
check("every malformed file is reported", len(rejected), len(cases))
check("the report names the file", any("list.json" in x for x in rejected), True)
check("a coerced field is reported too, not silently fixed",
      any("agents.json" in x and "not a list" in x for x in rejected), True)

# The coercions keep a partially-malformed trace usable rather than discarding it.
open(os.path.join(d, "coerce.json"), "w").write(
    '{"schema":"wellforge-run/v3","run_id":"c","feature":"f",'
    '"agents":"nope","verdicts":{"qe":"PASS"}}')
rej2 = []
runs2 = rr.load_runs(d, "", rej2)
c = [r for r in runs2 if r.get("run_id") == "c"][0]
check("a non-list `agents` becomes []", c["agents"], [])
check("...and the trace keeps its verdicts", c["verdicts"], {"qe": "PASS"})

# The downstream aggregations must survive the coerced shapes too — this is where
# `.items()` on a string and `.get()` on None used to raise.
rr.rework(runs2)
rr.attribute([], runs2)
check("rework/attribute run over coerced traces", True, True)
_sh.rmtree(d, ignore_errors=True)

# Advisor sub-inferences: billed at the ADVISOR's rate, absent from the executor's usage.
# A report that drops them makes "sonnet + opus advisor" look like plain sonnet — the OpEx
# trap model-routing.yml warns about, in the direction of looking cheap.
adv = ev("10:05", 1_000_000, 0, "wellforge:backend-dev", model="claude-sonnet-5-5")
adv.update({"advisor_calls": 2, "advisor_model": "claude-opus-5-5",
            "advisor_input_tokens": 1_000_000, "advisor_output_tokens": 0})
check("executor tokens exclude the advisor's", rr.totals([adv], PRICING)[:2], (1_000_000, 0))
check("cost = sonnet input + opus input (2.00 + 5.00)", rr.totals([adv], PRICING)[2], 7.0)
check("advisor totals", rr.advisor_totals([adv]),
      {"calls": 2, "input_tokens": 1_000_000, "output_tokens": 0, "tokens_known": True})

nodata = ev("10:06", 1, 1, "qe")
nodata["advisor_calls"] = 1
check("a call with no token data is counted, tokens flagged as a floor",
      rr.advisor_totals([adv, nodata])["calls"], 3)
check("tokens_known false when any call lacked token data",
      rr.advisor_totals([adv, nodata])["tokens_known"], False)
check("no advisor → zero calls, tokens known",
      rr.advisor_totals([ev("10:05", 1, 1)]), {"calls": 0, "input_tokens": 0,
                                                "output_tokens": 0, "tokens_known": True})

# Rework names the advised agents, normalised from the plugin-prefixed agent_type.
adv_runs = [_mkrun("r-adv", "001-x", "mvp", {"qe": "FAIL"}, ["backend-dev"])]
adv_runs[0]["run_id"] = "r-adv"
rw_adv = rr.rework(adv_runs, {"r-adv": [adv]})
check("rework: advisor calls by agent", rw_adv["advisor_calls_by_agent"], {"backend-dev": 2})
check("rework without events: empty advised map", rr.rework(adv_runs)["advisor_calls_by_agent"], {})

# ── Measured cost (OTel) ─────────────────────────────────────────────────────────────
# Shapes from a real Claude Code 2.1.322 export, reduced to what otel-sink.py keeps.
def req(ts, cost, agent_id=None, agent_name=None, rid=None, cache_read=0):
    q = {"event.name": "api_request", "ts": ts, "cost_usd": cost, "input_tokens": 2,
         "output_tokens": 10, "cache_read_tokens": cache_read, "cache_creation_tokens": 0}
    if agent_id:
        q["agent_id"] = agent_id
        q["agent.name"] = agent_name or "backend-dev"
    if rid:
        q["request_id"] = rid
    return q


# 11. agent_id joins a subagent's requests to the run its SubagentStop event belongs to —
#     exactly, even when the two parallel runs' windows overlap and the names would not split.
runs = [run("be", "backend-dev", "10:00", "10:10"), run("fe", "frontend-dev", "10:01", "10:09")]
hook = {"be": [dict(ev("10:05", 1, 1, "wellforge:backend-dev"), agent_id="A1")],
        "fe": [dict(ev("10:06", 1, 1, "wellforge:frontend-dev"), agent_id="A2")]}
reqs = [req("10:04", 0.30, "A1", "wellforge:backend-dev"), req("10:05", 0.20, "A2", "wellforge:frontend-dev"),
        req("10:05", 0.50)]  # main loop, inside BOTH windows
by, outside, amb = rr.attribute_otel(reqs, runs, hook)
check("agent_id joins be", [q["cost_usd"] for q in by["be"]], [0.30])
check("agent_id joins fe", [q["cost_usd"] for q in by["fe"]], [0.20])
check("main loop in two windows → ambiguous, not doubled", ([q["cost_usd"] for q in amb], outside), ([0.50], []))

# 12. A subagent whose stop event was lost: window + agent name (plugin prefix stripped).
by, _, amb = rr.attribute_otel([req("10:05", 0.40, "A9", "wellforge:frontend-dev")], runs, {})
check("lost stop event → narrowed by agent.name", ([q["cost_usd"] for q in by["fe"]], amb), ([0.40], []))

# 13. Sequential runs: the main loop is attributed by window; work outside every run is outside.
seq = [run("r1", "backend-dev", "10:00", "10:10"), run("r2", "qe", "11:00", "11:10")]
by, outside, amb = rr.attribute_otel([req("10:02", 0.1), req("11:05", 0.2), req("12:00", 0.7)], seq, {})
check("sequential main loop by window", ([q["cost_usd"] for q in by["r1"]], [q["cost_usd"] for q in by["r2"]]),
      ([0.1], [0.2]))
check("outside every run", [q["cost_usd"] for q in outside], [0.7])

# 14. measured(): main vs subagent split, cache tokens counted, garbage cost ignored.
m = rr.measured([req("10:00", 0.25, "A1", cache_read=1000), req("10:01", 0.75), dict(req("10:02", 0), cost_usd="x")])
check("measured split", (m["cost_usd"], m["main_usd"], m["subagent_usd"], m["cache_read_tokens"], m["requests"]),
      (1.0, 0.75, 0.25, 1000, 3))

# 15. End to end through main(): session markers select the spool files, OTel ms timestamps
#     compare correctly against second-resolution windows, a retried batch is not doubled,
#     another project's session is never read, and the budget uses the measured basis.
with tempfile.TemporaryDirectory() as d:
    runs_dir, spool = os.path.join(d, "runs"), os.path.join(d, "spool")
    os.makedirs(runs_dir)
    os.makedirs(spool)
    trace = {"schema": "wellforge-run/v3", "run_id": "2026-11-24T10-00-00Z-implement-001-x",
             "command": "implement", "feature": "001-x", "rigor": "mvp", "result": "complete",
             "started": "2026-11-24T10:00:00Z", "finished": "2026-11-24T10:00:37Z",
             "agents": [{"agent": "backend-dev"}], "verdicts": {}}
    json.dump(trace, open(os.path.join(runs_dir, trace["run_id"] + ".json"), "w"))
    with open(os.path.join(runs_dir, ".events.jsonl"), "w") as f:
        f.write(json.dumps({"ts": "2026-11-24T09:59:00Z", "event": "session_start", "session_id": "S1"}) + "\n")
        f.write(json.dumps({"ts": "2026-11-24T10:00:30Z", "event": "subagent_stop", "session_id": "S1",
                            "agent_type": "wellforge:backend-dev", "agent_id": "A1",
                            "model": "claude-sonnet-5", "input_tokens": 100, "output_tokens": 50}) + "\n")
    rec = {"event.name": "api_request", "session.id": "S1", "model": "claude-sonnet-5"}
    with open(os.path.join(spool, "S1.jsonl"), "w") as f:
        for line in (dict(rec, **{"event.timestamp": "2026-11-24T10:00:00.500Z", "cost_usd": 1.5,
                                  "request_id": "q1"}),                 # FIRST second: "…00.500Z" < "…00Z" as strings
                     dict(rec, **{"event.timestamp": "2026-11-24T10:00:10.000Z", "cost_usd": 2.0,
                                  "request_id": "q2", "agent_id": "A1", "agent.name": "wellforge:backend-dev"}),
                     dict(rec, **{"event.timestamp": "2026-11-24T10:00:10.000Z", "cost_usd": 2.0,
                                  "request_id": "q2", "agent_id": "A1"}),  # exporter retry
                     dict(rec, **{"event.timestamp": "2026-11-24T10:00:20.000Z", "event.name": "subagent_completed"})):
            f.write(json.dumps(line) + "\n")
    json.dump({"event.name": "api_request", "session.id": "OTHER", "event.timestamp": "2026-11-24T10:00:05Z",
               "cost_usd": 99.0}, open(os.path.join(spool, "OTHER.jsonl"), "w"))
    import subprocess
    out = subprocess.run([sys.executable, os.path.join(HERE, "..", "run-report.py"), "--runs-dir", runs_dir,
                          "--otel-spool", spool, "--json", "--budget"], capture_output=True, text=True)
    env = json.loads(out.stdout)
    r0 = env["runs"][0]
    check("e2e measured cost (retry de-duplicated, other session ignored)", r0["cost_usd"], 3.5)
    check("e2e source + split", (r0["cost_source"], r0["cost_main_usd"], r0["cost_subagent_usd"]), ("otel", 1.5, 2.0))
    check("e2e the session marker is not a token event", r0["events"], 1)
    check("e2e envelope", (env["cost_measured"], env["otel_outside_runs_usd"]), (True, 0.0))
    pf = env["budget"]["per_feature"][0]
    check("e2e budget on the measured basis", (pf["basis"], pf["spent_usd"], pf["state"]), ("otel", 3.5, "within"))
    out = subprocess.run([sys.executable, os.path.join(HERE, "..", "run-report.py"), "--runs-dir", runs_dir,
                          "--otel-spool", spool, "--json", "--budget", "--no-otel"], capture_output=True, text=True)
    env = json.loads(out.stdout)
    check("--no-otel falls back to the estimate",
          (env["runs"][0]["cost_source"], env["cost_measured"], env["budget"]["per_feature"][0]["basis"]),
          ("estimate", False, "estimate"))

print(f"\nrun-report: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
