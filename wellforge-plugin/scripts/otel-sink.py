#!/usr/bin/env python3
"""WellForge OTel sink — a local OTLP/HTTP-JSON receiver for Claude Code's cost events.

  otel-sink.py serve  [--port P] [--spool DIR] [--idle-exit SECONDS]
  otel-sink.py ensure [--port P] [--spool DIR]   # start a detached `serve` unless one answers
  otel-sink.py status [--port P]                 # exit 0 when a WellForge sink answers

Why it exists: Claude Code prices every API call itself — `cost_usd` on the `api_request`
log event, cache tokens included, main loop included, and `agent_id` / `agent.name` on a
subagent's calls — but it only EXPORTS that over OTLP, never to a file. run-report.py needs
it on disk, per session, without a collector the team has to run. This is the smallest
thing that does that, and nothing more (see skills/observability "Measured cost").

What it keeps, and why so little: an `api_request` or `subagent_completed` record, reduced to
the allowlist below. Claude Code's log stream also carries the user's e-mail and account ids
on every record, and — when the operator turned those on — prompt and response text. None of
that is needed to price a run, so none of it is written. An allowlist, not a denylist: a new
attribute Claude Code adds tomorrow is dropped until someone decides it belongs here.

Bound to 127.0.0.1 only. Stdlib only. Exits on its own after --idle-exit seconds with no
traffic, so a sink nobody needs any more does not live forever; the next SessionStart starts
a fresh one.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 14318  # not 4317/4318: those belong to a real collector the user may run
HEALTH_PATH = "/wellforge-otel-sink"
KEEP_EVENTS = {"api_request", "subagent_completed"}
KEEP_ATTRS = {
    "event.name", "event.timestamp", "session.id", "prompt.id", "request_id",
    "model", "query_source", "agent_id", "agent.name", "agent_type",
    "cost_usd", "input_tokens", "output_tokens", "cache_read_tokens",
    "cache_creation_tokens", "duration_ms", "total_tokens", "total_tool_uses",
}


def default_port():
    try:
        return int(os.environ.get("WF_OTEL_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT


def default_spool():
    if os.environ.get("WF_OTEL_SPOOL"):
        return os.environ["WF_OTEL_SPOOL"]
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "wellforge", "otel")


def _value(v):
    """An OTLP AnyValue → a plain value. Ints arrive as strings in OTLP/JSON."""
    if not isinstance(v, dict) or not v:
        return None
    if "intValue" in v:
        try:
            return int(v["intValue"])
        except (TypeError, ValueError):
            return None
    if "doubleValue" in v:
        return v["doubleValue"]
    for k in ("stringValue", "boolValue"):
        if k in v:
            return v[k]
    return None


def _attrs(lst):
    out = {}
    for a in lst or []:
        if isinstance(a, dict) and "key" in a:
            out[a["key"]] = _value(a.get("value"))
    return out


def extract(body):
    """OTLP/JSON logs payload → the reduced records worth keeping. Pure, so it is testable."""
    out = []
    for rl in (body or {}).get("resourceLogs", []) or []:
        res = _attrs(((rl or {}).get("resource") or {}).get("attributes"))
        for sl in (rl or {}).get("scopeLogs", []) or []:
            for lr in (sl or {}).get("logRecords", []) or []:
                a = _attrs((lr or {}).get("attributes"))
                name = (a.get("event.name") or "").removeprefix("claude_code.")
                if name not in KEEP_EVENTS:
                    continue
                a["event.name"] = name
                rec = {k: v for k, v in a.items() if k in KEEP_ATTRS and v is not None}
                sid = rec.get("session.id") or res.get("session.id")
                if not sid:
                    continue
                rec["session.id"] = sid
                if res.get("service.version"):
                    rec["claude_code.version"] = res["service.version"]
                out.append(rec)
    return out


def _safe_name(sid):
    return "".join(c for c in str(sid) if c.isalnum() or c in "-_")[:80] or "unknown"


def write_records(spool, records):
    os.makedirs(spool, exist_ok=True)
    by_sid = {}
    for r in records:
        by_sid.setdefault(_safe_name(r["session.id"]), []).append(r)
    for sid, recs in by_sid.items():
        with open(os.path.join(spool, f"{sid}.jsonl"), "a") as f:
            for r in recs:
                f.write(json.dumps(r, sort_keys=True) + "\n")


def make_handler(spool, touch):
    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            if self.path == HEALTH_PATH:
                self._reply(200, {"wellforge": "otel-sink", "spool": spool})
            else:
                self._reply(404, {})

        def do_POST(self):  # noqa: N802
            touch()
            n = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(n) if n else b""
            ctype = (self.headers.get("content-type") or "").split(";")[0].strip()
            if ctype != "application/json":
                # protobuf would need a dependency; the documented setting is http/json
                self._reply(415, {"error": "set OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=http/json"})
                return
            if self.path.rstrip("/").endswith("/v1/logs"):
                try:
                    write_records(spool, extract(json.loads(raw or b"{}")))
                except (ValueError, OSError):
                    pass  # telemetry must never become an error the exporter retries forever
            # metrics/traces: accepted and dropped — the logs carry everything run-report needs
            self._reply(200, {})

        def log_message(self, *a):
            pass

    return Handler


def serve(port, spool, idle_exit):
    last = [time.monotonic()]
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(spool, lambda: last.__setitem__(0, time.monotonic())))
    if idle_exit > 0:
        def reaper():
            while True:
                time.sleep(min(60, idle_exit))
                if time.monotonic() - last[0] > idle_exit:
                    srv.shutdown()
                    return
        threading.Thread(target=reaper, daemon=True).start()
    srv.serve_forever()
    return 0


def answers(port, timeout=0.5):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{HEALTH_PATH}", timeout=timeout) as r:
            return json.loads(r.read() or b"{}").get("wellforge") == "otel-sink"
    except Exception:  # noqa: BLE001
        return False


def ensure(port, spool, idle_exit):
    if answers(port):
        return 0
    subprocess.Popen(
        [sys.executable, "-I", os.path.abspath(__file__), "serve", "--port", str(port),
         "--spool", spool, "--idle-exit", str(idle_exit)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True, close_fds=True)
    for _ in range(20):
        if answers(port, 0.2):
            return 0
        time.sleep(0.1)
    # Something else holds the port, or the sink could not start. Not an error a session
    # should see — run-report will say "no measured cost" for these sessions.
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["serve", "ensure", "status"])
    ap.add_argument("--port", type=int, default=default_port())
    ap.add_argument("--spool", default=default_spool())
    try:
        idle = int(os.environ.get("WF_OTEL_IDLE_EXIT", 12 * 3600))
    except ValueError:
        idle = 12 * 3600
    ap.add_argument("--idle-exit", type=int, default=idle)
    a = ap.parse_args()
    if a.action == "serve":
        return serve(a.port, a.spool, a.idle_exit)
    if a.action == "ensure":
        return ensure(a.port, a.spool, a.idle_exit)
    return 0 if answers(a.port) else 1


if __name__ == "__main__":
    sys.exit(main())
