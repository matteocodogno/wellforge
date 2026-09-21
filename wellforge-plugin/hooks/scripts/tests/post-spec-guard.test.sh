#!/usr/bin/env bash
# Regression matrix for post-spec-guard.sh — the lifecycle rules as mechanism, not promise.
#
# Each case is a real frontmatter transition on a fixture project, driven through the REAL
# hook. The rules under test: only a met gate may write `status: done`, rigor never goes
# down, a closed feature does not silently reopen, and a status outside the enum never
# lands at all. Every one of these was a prompt promise until 2026-09-20.
set -uo pipefail
HOOK="$(cd "$(dirname "$0")/.." && pwd)/post-spec-guard.sh"
PASS=0; FAIL=0

new_project() {
  REPO=$(mktemp -d)
  git init -q -b main "$REPO"
  git -C "$REPO" config user.email t@t; git -C "$REPO" config user.name T
  git -C "$REPO" config commit.gpgsign false
  mkdir -p "$REPO/specs/001-x" "$REPO/.forge/runs"
}

spec() {  # spec <status> [rigor]
  local status="$1" rigor="${2:-production}"
  { echo "---"; echo "id: 001"; echo "slug: x"; echo "status: $status"; echo "rigor: $rigor"
    [ "$status" = done ] && echo "done: 2026-09-20"
    echo "---"; echo; echo "# X"; } > "$REPO/specs/001-x/spec.md"
}

tasks() {  # tasks <checked> <total>
  { echo "---"; echo "spec: 001"; echo "---"; echo
    local i=0
    while [ $i -lt "$1" ]; do echo "- [x] T$((i+1)): done"; i=$((i+1)); done
    while [ $i -lt "$2" ]; do echo "- [ ] T$((i+1)): todo"; i=$((i+1)); done; } > "$REPO/specs/001-x/tasks.md"
}

qe_pass() {
  cat > "$REPO/.forge/runs/r1.json" <<JSON
{"schema":"wellforge-run/v1","run_id":"r1","command":"implement","feature":"001-x",
 "rigor":"production","started":"2026-09-01T10:00:00Z","finished":"2026-09-01T10:30:00Z",
 "agents":[],"drift_events":[],"verdicts":{"qe":"PASS","security":"PASS","eval":"PASS"}}
JSON
  printf -- '---\nspec: 001\nverdict: PASS\nscore: 90\n---\n' > "$REPO/specs/001-x/eval-report.md"
}

commit_all() { git -C "$REPO" add -A >/dev/null; git -C "$REPO" commit -qm "fixture" >/dev/null; }

run() {  # run <want-exit> <desc> [file]
  local want="$1" desc="$2" file="${3:-$REPO/specs/001-x/spec.md}" out got
  out=$(printf '{"tool_input":{"file_path":"%s"}}' "$file" \
        | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1); got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1));
  else FAIL=$((FAIL+1)); echo "  FAIL: $desc (want exit $want, got $got)"; echo "$out" | sed 's/^/        /'; fi
}

echo "post-spec-guard matrix"

# 1. draft → approved: an ordinary, legal transition
new_project; spec draft; tasks 0 0; commit_all; spec approved
run 0 "draft → approved is allowed"

# 2. approved → in-progress
new_project; spec approved; commit_all; spec in-progress
run 0 "approved → in-progress is allowed"

# 3. in-progress → done with the gate MET
new_project; spec in-progress; tasks 2 2; qe_pass; commit_all; spec done
run 0 "in-progress → done with a passing gate is allowed"

# 4. in-progress → done with the gate FAILING (unchecked tasks, no QE)
new_project; spec in-progress; tasks 1 3; commit_all; spec done
run 2 "in-progress → done with a failing gate is blocked"

# 4b. Production reviews every batch, so an ABSENT security verdict is a failing gate —
#     a feature can pass every test and still ship an unreviewed auth change.
new_project; spec in-progress; tasks 2 2; qe_pass
python3 - "$REPO" <<'PYFIX'
import json, sys, glob, os
for p in glob.glob(os.path.join(sys.argv[1], ".forge", "runs", "*.json")):
    r = json.load(open(p)); r["verdicts"].pop("security", None); json.dump(r, open(p, "w"))
PYFIX
commit_all; spec done
run 2 "in-progress → done without a security verdict is blocked at production"

# 5. rigor lowered
new_project; spec in-progress production; commit_all; spec in-progress mvp
run 2 "rigor production → mvp is blocked"

# 6. rigor raised
new_project; spec in-progress mvp; commit_all; spec in-progress production
run 0 "rigor mvp → production is allowed"

# 7. done → superseded (a sanctioned retirement)
new_project; spec done; tasks 1 1; qe_pass; commit_all
{ echo "---"; echo "id: 001"; echo "slug: x"; echo "status: superseded"
  echo "rigor: production"; echo "superseded_by: 002-y"; echo "---"; } > "$REPO/specs/001-x/spec.md"
run 0 "done → superseded is allowed"

# 8. done → draft (reopening by edit)
new_project; spec done; tasks 1 1; qe_pass; commit_all; spec draft
run 2 "done → draft is blocked"

# 9. a brand-new spec file (untracked, status draft) must never be blocked
new_project; commit_all 2>/dev/null || true
mkdir -p "$REPO/specs/002-new"
printf -- '---\nid: 002\nslug: new\nstatus: draft\nrigor: production\n---\n\n# New\n' > "$REPO/specs/002-new/spec.md"
run 0 "a new spec at status draft is allowed" "$REPO/specs/002-new/spec.md"

# 10. an edit outside specs/ is a no-op
new_project; spec draft; commit_all
echo "x" > "$REPO/README.md"
run 0 "an edit outside specs/ is a no-op" "$REPO/README.md"

# ── the rules the brief did not enumerate, which the hook also has to hold ──────
# 11. a status outside the enum never lands, whatever the transition
new_project; spec draft; commit_all; spec doen
run 2 "a status outside the lifecycle enum is blocked"

# 12. a rigor outside the enum
new_project; spec draft production; commit_all; spec draft prod
run 2 "a rigor outside the enum is blocked"

# 13. the spike carve-out: a brief closes on prose, so the gate cannot be checked
new_project; rm -f "$REPO/specs/001-x/spec.md"
printf -- '---\nid: 001\nslug: x\nstatus: in-progress\nrigor: spike\n---\n\n# X\n' > "$REPO/specs/001-x/brief.md"
commit_all
printf -- '---\nid: 001\nslug: x\nstatus: done\ndone: 2026-09-20\nrigor: spike\n---\n\n# X\n' > "$REPO/specs/001-x/brief.md"
run 0 "a spike brief closing is allowed (gate not machine-checkable)" "$REPO/specs/001-x/brief.md"

# 14. no WellForge project → the hook must not fire at all
REPO=$(mktemp -d); mkdir -p "$REPO/other"
printf -- '---\nstatus: done\n---\n' > "$REPO/other/spec.md"
run 0 "outside a WellForge project the hook no-ops" "$REPO/other/spec.md"

# 15. an unrelated edit to a spec (body only) passes
new_project; spec in-progress; commit_all
printf -- '\nmore prose\n' >> "$REPO/specs/001-x/spec.md"
run 0 "a body-only edit is allowed"

# 16. CARVE-OUT: a NEW spec written already `done` is a record of prior work, not a
#     transition — a retro spec for a brownfield adoption can never satisfy a gate about
#     tasks and QE runs that predate it.
new_project; commit_all
mkdir -p "$REPO/specs/003-legacy"
printf -- '---\nid: 003\nslug: legacy\nstatus: done\ndone: 2026-01-01\nrigor: production\n---\n' \
  > "$REPO/specs/003-legacy/spec.md"
run 0 "a NEW spec created already done is allowed (record, not transition)" "$REPO/specs/003-legacy/spec.md"

# 17. ...but the same status on an EXISTING spec is still the gated transition.
new_project; spec in-progress; tasks 0 2; commit_all; spec done
run 2 "an existing spec moving to done still faces the gate"

# 18. The refusal must carry the actual failing reasons, not a generic message: the numbers
#     are the only part that says how far from done the feature is.
out=$(printf '{"tool_input":{"file_path":"%s"}}' "$REPO/specs/001-x/spec.md" \
      | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1)
if echo "$out" | grep -q "2 of 2 tasks unchecked" && echo "$out" | grep -q "/wellforge:done" \
   && echo "$out" | grep -qi "revert"; then
  PASS=$((PASS+1))
else
  FAIL=$((FAIL+1)); echo "  FAIL: refusal must quote the failing reasons, the command and the revert"
  echo "$out" | sed 's/^/        /'
fi

# ── 19-21. the OTHER two terminal states ───────────────────────────────────────────
# done.md calls done/archived/superseded "the three terminal states" and the README says
# there is no reopening by edit, but the rule only ever guarded `done →`. The two states
# whose entire meaning is "closed" were the two nobody checked.
new_project; spec archived; commit_all; spec in-progress
run 2 "archived → in-progress is blocked"

new_project; spec superseded; commit_all; spec draft
run 2 "superseded → draft is blocked"

new_project; spec done; tasks 2 2; qe_pass; commit_all; spec archived
run 0 "done → archived is still allowed (a sanctioned retirement)"

# ── 22-24. rigor: a spec with no `rigor:` is at the project default, i.e. production ──
# Adding `rigor: spike` to it is a LOWERING, and it was the one spelling that needed no
# edit to an existing value — so the old `-n "$OLD_RIGOR"` test waved it straight through.
new_project
{ echo "---"; echo "id: 001"; echo "slug: x"; echo "status: in-progress"; echo "---"; echo; echo "# X"; } \
  > "$REPO/specs/001-x/spec.md"
commit_all
{ echo "---"; echo "id: 001"; echo "slug: x"; echo "status: in-progress"; echo "rigor: spike"
  echo "---"; echo; echo "# X"; } > "$REPO/specs/001-x/spec.md"
run 2 "ADDING rigor: spike to a spec that had none (implicitly production) is blocked"

# Creating a brand-new spike spec is not lowering anything — the carve-out that keeps the
# rule above from being a false positive on every new spike.
new_project
mkdir -p "$REPO/specs/004-probe"
{ echo "---"; echo "id: 004"; echo "slug: probe"; echo "status: draft"; echo "rigor: spike"
  echo "---"; echo; echo "# probe"; } > "$REPO/specs/004-probe/spec.md"
run 0 "a NEW spec created at rigor: spike is allowed" "$REPO/specs/004-probe/spec.md"

new_project; spec in-progress spike; commit_all; spec in-progress production
run 0 "raising spike → production is allowed"

# ── 25-27. field(): quoted and unspaced scalars are valid YAML and meant what they said ──
# `status: 'done'` returned the literal `'done'`, which equals no known status, so every
# rule comparing against done silently did not fire. `status:done` read as empty, so the
# guard concluded nothing it polices had changed. Both were bypasses by typography.
# The exit code alone does not discriminate here: an unstripped `'done'` is not in the
# status enum either, so the old hook also refused — but for the WRONG reason, telling the
# author their status was invalid when the real objection is the unmet gate. Assert the
# REASON, which is the part that was wrong.
for quoted in "status: 'done'" 'status: "done"'; do
  new_project; spec in-progress; tasks 0 2; commit_all
  # `done:` is required by the schema whenever status is done — without it the refusal is
  # about frontmatter, which would not test the gate at all.
  { echo "---"; echo "id: 001"; echo "slug: x"; echo "$quoted"; echo "rigor: production"
    echo "done: 2026-09-20"; echo "---"; echo; echo "# X"; } > "$REPO/specs/001-x/spec.md"
  out=$(printf '{"tool_input":{"file_path":"%s"}}' "$REPO/specs/001-x/spec.md" \
        | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1); got=$?
  if [ "$got" = 2 ] && echo "$out" | grep -q "tasks unchecked" \
     && ! echo "$out" | grep -qi "outside the enum"; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1))
    echo "  FAIL: $quoted must be refused BY THE GATE (unchecked tasks), not as an invalid status"
    echo "$out" | sed 's/^/        /'
  fi
done

new_project; spec in-progress; tasks 0 2; commit_all
{ echo "---"; echo "id: 001"; echo "slug: x"; echo "status:done"; echo "rigor: production"
  echo "---"; echo; echo "# X"; } > "$REPO/specs/001-x/spec.md"
run 2 "status:done (no space) still faces the gate"

# ── 28-29. a broken gate is not a passing gate ──────────────────────────────────────
# One malformed trace in .forge/runs/ used to crash forge-state.py, and the hook read the
# empty result as "could not evaluate" and allowed the edit UNVERIFIED. So a single
# unparseable file silently switched the done gate off.
new_project; spec in-progress; tasks 2 2; qe_pass; commit_all
printf '[1]' > "$REPO/.forge/runs/broken.json"
spec done
run 2 "a malformed run trace refuses the edit instead of failing open"

out=$(printf '{"tool_input":{"file_path":"%s"}}' "$REPO/specs/001-x/spec.md" \
      | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1)
if echo "$out" | grep -qi "broken.json\|run trace\|forge-state"; then
  PASS=$((PASS+1))
else
  FAIL=$((FAIL+1)); echo "  FAIL: the refusal must name the unreadable trace, not just refuse"
  echo "$out" | sed 's/^/        /'
fi

echo
echo "post-spec-guard: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
