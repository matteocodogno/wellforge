#!/usr/bin/env sh
# Refuse to touch a database that does not belong to this checkout.
#
#   mise run db:guard              # check the configured target
#   sh .wellforge/db-guard.sh <url-or-dbname>
#
# Why this exists (docs/adr/0002-per-worktree-databases.md): a git worktree isolates the
# CHECKOUT and nothing else. Two worktrees resolve the same database name to the same
# object, so one can drop or migrate the database another is mid-test against. The failure
# does not look like a collision — it looks like your code broke.
#
# `WF_DB_NAME` is this checkout's expected database (mise derives it from the worktree
# identity). This script compares the target anything is about to be run against with that
# expectation and refuses on a mismatch. It is a ratchet on the sanctioned path, not a
# sandbox: a connection string built by hand inside application code is not visible here.
set -eu

expected=${WF_DB_NAME:-}

if [ -z "$expected" ]; then
  # Two very different situations, and conflating them broke `mise run test` for every
  # project generated with db=none. mise always exports WF_WT_SUFFIX (empty in the primary
  # tree, hence the ${x+set} presence test rather than -z), so its presence is what says
  # mise ran at all.
  if [ -n "${WF_WT_SUFFIX+set}" ]; then
    echo "db:guard OK — this project has no database configured (db=none); nothing to guard"
    exit 0
  fi
  cat >&2 <<'GUARD_EOF'
db:guard — neither WF_DB_NAME nor WF_WT_SUFFIX is set, so this did not run through mise
and there is nothing to compare against.

Those variables are derived by mise from this checkout's identity. Run the task through
mise (`mise run …`), and `mise trust` this directory if you have not yet: an untrusted
config resolves to nothing rather than failing loudly, which is exactly how two worktrees
end up sharing one database.
GUARD_EOF
  exit 1
fi

# Target precedence: an explicit argument, then whatever the app would actually use.
target_raw=${1:-}
source="argument"
if [ -z "$target_raw" ]; then
  if [ -n "${DATABASE_URL:-}" ]; then
    target_raw=$DATABASE_URL; source="DATABASE_URL"
  elif [ -n "${SPRING_DATASOURCE_URL:-}" ]; then
    target_raw=$SPRING_DATASOURCE_URL; source="SPRING_DATASOURCE_URL"
  fi
fi

if [ -z "$target_raw" ]; then
  # No explicitly configured target. For the JVM preset this is the NORMAL case: Spring
  # Boot's docker-compose support derives the datasource from the container it started,
  # which already carries WF_DB_NAME. Nothing is being pointed anywhere unexpected.
  echo "db:guard OK — no explicit database target configured; the stack resolves its own"
  echo "             (expected database for this checkout: $expected)"
  exit 0
fi

# Database name = last path segment, minus any query string. Works for
# postgres://u:p@h:5432/name?sslmode=…  and  jdbc:postgresql://h:5432/name?…
target_db=${target_raw%%\?*}
target_db=${target_db##*/}

if [ -z "$target_db" ]; then
  echo "db:guard: could not read a database name out of the $source target" >&2
  echo "          value (credentials not printed): …/${target_raw##*/}" >&2
  exit 1
fi

if [ "$target_db" != "$expected" ]; then
  wt=$(sh "$(dirname "$0")/worktree-id.sh" id 2>/dev/null || echo unknown)
  linked=$(sh "$(dirname "$0")/worktree-id.sh" linked 2>/dev/null || echo unknown)
  cat >&2 <<EOF
db:guard REFUSED — this checkout would act on a database that is not its own.

  checkout        $(git rev-parse --show-toplevel 2>/dev/null || pwd)
  worktree id     $wt   (linked worktree: $linked)
  expected db     $expected
  target db       $target_db      (from $source)

A linked worktree gets its own database precisely so a parallel agent cannot drop or
migrate the one another worktree is testing against. Acting on '$target_db' from here is
the collision this guard exists to stop, and it would surface later as tests failing in
code that is fine.

If you MEANT to target a shared database, that is a deliberate act, not a default: set
WF_DB_NAME to '$target_db' for this invocation and the guard will agree with you.
EOF
  exit 1
fi

echo "db:guard OK — $source targets '$target_db', which is this checkout's own database"
