#!/usr/bin/env python3
"""Regression matrix for otel-sink.py — the local receiver for Claude Code's cost events.

What must never regress:
  - the ALLOWLIST: Claude Code puts the user's e-mail and account ids on every record, and
    prompt/response text on some; none of it may reach the spool;
  - only `api_request` / `subagent_completed` are kept, one file per session;
  - protobuf is refused loudly (415), not silently swallowed as "no cost";
  - `ensure` starts exactly one sink and is a no-op when one answers; idle exit works.

The record shapes below are copied from a real Claude Code 2.1.322 export (2026-11-24),
reduced. Run: wellforge-plugin/scripts/tests/otel-sink.test.py
"""
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SINK = os.path.join(HERE, "..", "otel-sink.py")
spec = importlib.util.spec_from_file_location("sink", SINK)
sink = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sink)

passed = failed = 0


def check(desc, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {desc}\n        want {want!r}\n        got  {got!r}")


def s(v):
    return {"stringValue": v}


def attrs(d):
    out = []
    for k, v in d.items():
        if isinstance(v, bool):
            out.append({"key": k, "value": {"boolValue": v}})
        elif isinstance(v, int):
            out.append({"key": k, "value": {"intValue": str(v)}})
        elif isinstance(v, float):
            out.append({"key": k, "value": {"doubleValue": v}})
        else:
            out.append({"key": k, "value": s(v)})
    return out


def payload(*records, sid_on_resource=False):
    res = {"service.name": "claude-code", "service.version": "2.1.322"}
    if sid_on_resource:
        res["session.id"] = "sess-res"
    return {"resourceLogs": [{"resource": {"attributes": attrs(res)},
                              "scopeLogs": [{"logRecords": [{"attributes": attrs(r)} for r in records]}]}]}


API_SUB = {"event.name": "api_request", "session.id": "sess-1", "event.timestamp": "2026-11-24T16:26:37.150Z",
           "model": "claude-haiku-5-5", "query_source": "agent:builtin:general-purpose",
           "agent_id": "a9cef7ebf662ce808", "agent.name": "general-purpose", "cost_usd": 0.004948325,
           "input_tokens": 2, "output_tokens": 114, "cache_read_tokens": 0, "cache_creation_tokens": 39129,
           "request_id": "req_1", "user.email": "someone@example.invalid", "user.account_uuid": "u-1",
           "organization.id": "org-1", "terminal.type": "non-interactive"}
API_MAIN = {"event.name": "api_request", "session.id": "sess-1", "event.timestamp": "2026-11-24T16:26:34.996Z",
            "model": "claude-haiku-5-5", "query_source": "sdk", "cost_usd": 0.00610817,
            "input_tokens": 2, "output_tokens": 209, "request_id": "req_2", "user.email": "someone@example.invalid"}
RESPONSE = {"event.name": "assistant_response", "session.id": "sess-1", "response": "SECRET TEXT",
            "model": "claude-haiku-5-5"}
PROMPT = {"event.name": "user_prompt", "session.id": "sess-1", "prompt": "SECRET PROMPT"}
DONE = {"event.name": "subagent_completed", "session.id": "sess-1", "agent_id": "a9cef7ebf662ce808",
        "agent_type": "general-purpose", "total_tokens": 39245, "user.email": "someone@example.invalid"}

print("otel-sink matrix")

# 1. extract keeps the two events, drops everything else.
recs = sink.extract(payload(API_SUB, API_MAIN, RESPONSE, PROMPT, DONE))
check("kept events", [r["event.name"] for r in recs], ["api_request", "api_request", "subagent_completed"])

# 2. The allowlist: no identity, no text, ever — on any kept record.
blob = json.dumps(recs)
for leaked in ("someone@example.invalid", "u-1", "org-1", "SECRET", "terminal.type"):
    check(f"{leaked!r} never kept", leaked in blob, False)
check("cost kept as a number", recs[0]["cost_usd"], 0.004948325)
check("ints decoded from OTLP strings", recs[0]["cache_creation_tokens"], 39129)
check("subagent identity kept", (recs[0]["agent_id"], recs[0]["agent.name"]),
      ("a9cef7ebf662ce808", "general-purpose"))
check("Claude Code version carried from the resource", recs[0]["claude_code.version"], "2.1.322")

# 3. A `claude_code.`-prefixed event name (older exporters) is the same event.
recs = sink.extract(payload(dict(API_MAIN, **{"event.name": "claude_code.api_request"})))
check("prefixed event name normalized", [r["event.name"] for r in recs], ["api_request"])

# 4. session.id on the resource instead of the record still files the record.
r = dict(API_MAIN)
del r["session.id"]
check("session from resource", sink.extract(payload(r, sid_on_resource=True))[0]["session.id"], "sess-res")
check("no session anywhere → dropped", sink.extract(payload(r)), [])

# 5. Garbage in, nothing out — never an exception.
for bad in (None, {}, {"resourceLogs": None}, {"resourceLogs": [None]}, {"resourceLogs": [{"scopeLogs": [None]}]}):
    check(f"garbage {bad!r}", sink.extract(bad), [])


def free_port():
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        return so.getsockname()[1]


def post(port, path, body, ctype="application/json"):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method="POST",
                                 headers={"content-type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


# 6. The server: one file per session, protobuf refused, metrics accepted and dropped.
with tempfile.TemporaryDirectory() as spool:
    port = free_port()
    t = threading.Thread(target=sink.serve, args=(port, spool, 0), daemon=True)
    t.start()
    for _ in range(50):
        if sink.answers(port, 0.2):
            break
        time.sleep(0.05)
    check("health answers", sink.answers(port), True)
    check("logs accepted", post(port, "/v1/logs", json.dumps(payload(API_SUB, RESPONSE)).encode()), 200)
    check("protobuf refused", post(port, "/v1/logs", b"\x0a\x00", "application/x-protobuf"), 415)
    check("metrics accepted", post(port, "/v1/metrics", b"{}"), 200)
    check("bad json does not 500", post(port, "/v1/logs", b"{not json"), 200)
    files = sorted(os.listdir(spool))
    check("one file per session", files, ["sess-1.jsonl"])
    lines = open(os.path.join(spool, "sess-1.jsonl")).read().splitlines()
    check("one record written", len(lines), 1)
    check("written record has no identity", "someone@example.invalid" in lines[0], False)

# 7. A session id cannot escape the spool directory.
check("path traversal neutralized", sink._safe_name("../../etc/passwd"), "etcpasswd")

# 8. ensure: starts a detached sink once, is a no-op when one answers, idle-exits.
with tempfile.TemporaryDirectory() as spool:
    port = free_port()
    env = dict(os.environ, WF_OTEL_PORT=str(port), WF_OTEL_SPOOL=spool, WF_OTEL_IDLE_EXIT="2")
    rc = subprocess.run([sys.executable, "-I", SINK, "ensure"], env=env, timeout=10).returncode
    check("ensure starts a sink", (rc, sink.answers(port)), (0, True))
    rc = subprocess.run([sys.executable, "-I", SINK, "ensure"], env=env, timeout=10).returncode
    check("second ensure is a no-op", rc, 0)
    rc = subprocess.run([sys.executable, "-I", SINK, "status"], env=env, timeout=10).returncode
    check("status sees it", rc, 0)
    deadline = time.time() + 10
    while time.time() < deadline and sink.answers(port, 0.2):
        time.sleep(0.5)
    check("idle sink exits on its own", sink.answers(port, 0.2), False)

print(f"\notel-sink: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
