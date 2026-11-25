#!/usr/bin/env bash
# Regression matrix for post-test-silencer-guard.sh — a red test is never silenced.
#
#   - an edit that ADDS a skip/disable/focus marker to a test file is blocked (exit 2),
#     in every language family the hook names;
#   - a marker that was already there, or one the edit removes, is not this agent's doing;
#   - Write compares against the file at HEAD (untracked = empty);
#   - non-test files and non-WellForge projects are never touched.
#
# Run: wellforge-plugin/hooks/scripts/tests/post-test-silencer-guard.test.sh
set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/post-test-silencer-guard.sh"
command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }

pass=0 fail=0
TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT
PROJ="$TMPROOT/proj"; mkdir -p "$PROJ/specs" "$PROJ/test" "$PROJ/src"
BARE="$TMPROOT/bare"; mkdir -p "$BARE/test"
git -C "$PROJ" init -q
printf 'import { test } from "node:test";\ntest.skip("legacy", () => {});\n' > "$PROJ/test/old.test.js"
git -C "$PROJ" add -A && git -C "$PROJ" -c user.name=t -c user.email=t@x.invalid commit -qm init

expect() {  # expect <name> <want-exit> <payload-json> [project-dir]
  local name="$1" want="$2" payload="$3" dir="${4:-$PROJ}" got
  printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$dir" bash "$HOOK" >/dev/null 2>"$TMPROOT/err"
  got=$?
  if [ "$got" = "$want" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf '  FAIL  %s: exit %s, want %s\n' "$name" "$got" "$want"
    sed 's/^/        /' "$TMPROOT/err"
  fi
}

edit() {  # edit <file> <old> <new>
  jq -cn --arg f "$1" --arg o "$2" --arg n "$3" \
    '{tool_name:"Edit", tool_input:{file_path:$f, old_string:$o, new_string:$n}}'
}
write() {  # write <file> <content>
  jq -cn --arg f "$1" --arg c "$2" '{tool_name:"Write", tool_input:{file_path:$f, content:$c}}'
}
multi() {  # multi <file> <old1> <new1> <old2> <new2>
  jq -cn --arg f "$1" --arg a "$2" --arg b "$3" --arg c "$4" --arg d "$5" \
    '{tool_name:"MultiEdit", tool_input:{file_path:$f, edits:[{old_string:$a,new_string:$b},{old_string:$c,new_string:$d}]}}'
}

T="$PROJ/test/orders.test.js"

echo "post-test-silencer-guard matrix"

# 1. Every family, added → blocked.
expect "js it.skip"          2 "$(edit "$T" 'it("pays", () => {' 'it.skip("pays", () => {')"
expect "js describe.only"    2 "$(edit "$T" 'describe("orders"' 'describe.only("orders"')"
expect "js test.todo"        2 "$(edit "$T" 'test("x", f)' 'test.todo("x")')"
expect "js xit("             2 "$(edit "$T" 'it("x", f)' 'xit("x", f)')"
expect "js skipIf"           2 "$(edit "$T" 'it("x", f)' 'it.skipIf(ci)("x", f)')"
expect "node:test skip opt"  2 "$(edit "$T" 'test("x", () => {' 'test("x", { skip: true }, () => {')"
expect "node:test t.skip("   2 "$(edit "$T" 'assert.ok(r)' 't.skip("flaky"); assert.ok(r)')"
expect "kotlin @Disabled"    2 "$(edit "$PROJ/src/test/kotlin/OrderTest.kt" '@Test' $'@Disabled\n@Test')"
expect "java @Ignore"        2 "$(edit "$PROJ/src/test/java/OrderTest.java" '@Test' $'@Ignore\n@Test')"
expect "kotest enabled=false" 2 "$(edit "$PROJ/src/test/kotlin/OrderSpec.kt" '"pays" {' '"pays".config(enabled = false) {')"
expect "pytest mark.skip"    2 "$(edit "$PROJ/tests/test_orders.py" 'def test_pay():' $'@pytest.mark.skip\ndef test_pay():')"
expect "pytest xfail"        2 "$(edit "$PROJ/tests/test_orders.py" 'def test_pay():' $'@pytest.mark.xfail\ndef test_pay():')"
expect "pytest.skip("        2 "$(edit "$PROJ/tests/test_orders.py" '    pay()' $'    pytest.skip("later")\n    pay()')"
expect "unittest.skip"       2 "$(edit "$PROJ/tests/test_orders.py" 'def test_pay(self):' $'@unittest.skip("x")\ndef test_pay(self):')"
expect "go t.Skip("          2 "$(edit "$PROJ/orders_test.go" 'func TestPay(t *testing.T) {' $'func TestPay(t *testing.T) {\n\tt.Skip("flaky")')"
expect "__tests__ dir"       2 "$(edit "$PROJ/src/__tests__/pay.ts" 'it("x"' 'it.skip("x"')"

# 2. Not added → allowed.
expect "marker removed"            0 "$(edit "$T" 'it.skip("pays", () => {' 'it("pays", () => {')"
expect "marker kept as it was"     0 "$(edit "$T" $'it.skip("legacy", () => {\n  a()' $'it.skip("legacy", () => {\n  b()')"
expect "ordinary test edit"        0 "$(edit "$T" 'assert.equal(r, 1)' 'assert.equal(r, 2)')"
expect "skip as plain word"        0 "$(edit "$T" '// TODO' '// we skip the header row')"
expect "focus-free fit word"       0 "$(edit "$T" 'const benefit = 1' 'const benefit = 2')"

# 3. MultiEdit: counted over every edit.
expect "multiedit adds one"   2 "$(multi "$T" 'a()' 'b()' 'it("x"' 'it.only("x"')"
expect "multiedit moves one"  0 "$(multi "$T" 'it.skip("x"' 'it("x"' 'it("y"' 'it.skip("y"')"

# 4. Write: against HEAD. old.test.js already has one skip at HEAD.
expect "write keeps HEAD skip"   0 "$(write "$PROJ/test/old.test.js" $'test.skip("legacy", () => {});\ntest("new", () => {});')"
expect "write adds a second"     2 "$(write "$PROJ/test/old.test.js" $'test.skip("legacy", () => {});\ntest.skip("new", () => {});')"
expect "write new file w/ skip"  2 "$(write "$PROJ/test/new.test.js" 'test.skip("x", () => {});')"
expect "write new file clean"    0 "$(write "$PROJ/test/new.test.js" 'test("x", () => {});')"

# 4b. Codex's runner: one payload per patched file, `file_path` only — compared on disk
#     against HEAD, because the patch has already been applied.
cpath() { jq -cn --arg f "$1" '{tool_name:"Edit", tool_input:{file_path:$f}}'; }
printf 'import { test } from "node:test";\ntest.skip("legacy", () => {});\n' > "$PROJ/test/old.test.js"
expect "codex: file as at HEAD"     0 "$(cpath "$PROJ/test/old.test.js")"
printf 'import { test } from "node:test";\ntest.skip("legacy", () => {});\ntest.only("new", () => {});\n' > "$PROJ/test/old.test.js"
expect "codex: patch added .only"   2 "$(cpath "$PROJ/test/old.test.js")"
printf 'import { test } from "node:test";\ntest("legacy", () => {});\n' > "$PROJ/test/old.test.js"
expect "codex: patch removed skip"  0 "$(cpath "$PROJ/test/old.test.js")"
git -C "$PROJ" checkout -q -- test/old.test.js
expect "codex: deleted file"        0 "$(cpath "$PROJ/test/gone.test.js")"

# 5. Scope.
expect "non-test file"       0 "$(edit "$PROJ/src/orders.js" 'run()' 'it.skip()')"
expect "bare project"        0 "$(edit "$BARE/test/a.test.js" 'it("x"' 'it.skip("x"')" "$BARE"
expect "other tool ignored"  0 '{"tool_name":"Read","tool_input":{"file_path":"x.test.js"}}'
expect "no file path"        0 '{"tool_name":"Edit","tool_input":{}}'

# 6. The message names the revert and the routes — an agent reads only this.
edit "$T" 'it("x"' 'it.skip("x"' | CLAUDE_PROJECT_DIR="$PROJ" bash "$HOOK" 2>"$TMPROOT/msg" >/dev/null
for want in "Revert" "ENV-FAULT" "spec/plan" "it.skip"; do
  if grep -q "$want" "$TMPROOT/msg"; then pass=$((pass + 1)); else fail=$((fail + 1)); printf '  FAIL  message lacks %s\n' "$want"; fi
done

printf 'post-test-silencer-guard: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
