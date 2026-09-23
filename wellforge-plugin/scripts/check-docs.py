#!/usr/bin/env python3
"""Docs drift guard — the plugin's README and CLAUDE.md must describe what ships.

Same idea as check-routing.py: the failure is silent (a command exists, nobody can find it),
so it needs a test rather than a convention. Reported 2026-09-20 with the README at 13/19
commands, 7/18 skills and one MCP server missing, and plugin.json one patch ahead of the
version CLAUDE.md quoted.

Checks:
  1. every commands/*.md appears in wellforge-plugin/README.md
  2. every skills/*/SKILL.md appears there too
  3. every server in .mcp.json appears there
  4. plugin.json's version == the version CLAUDE.md quotes, the version the marketplace
     entry publishes, AND the plugin tag its `ref` pins — three files naming one release
  5. every skill description is within the 1024-char limit the loader enforces
  6. cross-skill links are relative markdown links that resolve, not inert [[wiki-links]]
  7. the status/rigor enums in config/spec-frontmatter.schema.json match the spec-driven
     and rigor-tiers skills — the skills stay the human-readable authority, the schema is
     the machine-readable mirror, and a mirror that drifts is worse than no mirror

Run: wellforge-plugin/scripts/check-docs.py   (needs pyyaml)
"""
import glob
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
ROOT = os.path.dirname(PLUGIN)
README = open(os.path.join(PLUGIN, "README.md")).read()
fail = []

cmds = sorted(os.path.basename(p)[:-3] for p in glob.glob(f"{PLUGIN}/commands/*.md"))
for c in cmds:
    if f"commands/{c}.md" not in README:
        fail.append(f"README does not list command `{c}`")

skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(f"{PLUGIN}/skills/*/SKILL.md"))
for s in skills:
    if f"skills/{s}/" not in README:
        fail.append(f"README does not list skill `{s}`")

mcp = json.load(open(f"{PLUGIN}/.mcp.json"))
for server in mcp.get("mcpServers", mcp):
    if server not in README:
        fail.append(f"README does not list MCP server `{server}`")

pj = json.load(open(f"{PLUGIN}/.claude-plugin/plugin.json"))["version"]
quoted = re.search(r"plugin `([0-9]+\.[0-9]+\.[0-9]+)`", open(f"{ROOT}/CLAUDE.md").read())
if not quoted:
    fail.append("CLAUDE.md no longer quotes a plugin version — the sync check cannot run")
elif quoted.group(1) != pj:
    fail.append(f"plugin.json is {pj} but CLAUDE.md says {quoted.group(1)} — bump both in one commit")

# The marketplace entry is what a NEW teammate installs. It carries the version twice (an
# explicit `version`, and the `ref` tag its git-subdir source is pinned to), so there are two
# more ways for one release to disagree with itself — and the symptom is a teammate silently
# installing a different plugin than the repo describes.
mkt = json.load(open(f"{ROOT}/.claude-plugin/marketplace.json"))
entry = next((e for e in mkt["plugins"] if e["name"] == "wellforge"), None)
if entry is None:
    fail.append("marketplace.json has no `wellforge` plugin entry")
else:
    if entry.get("version") != pj:
        fail.append(f"marketplace.json publishes version {entry.get('version')} but "
                    f"plugin.json is {pj} — bump both in one commit")
    src = entry.get("source")
    if not isinstance(src, dict):
        fail.append(f"marketplace.json source is {src!r}, not a git source — a local path "
                    f"installs for nobody but the machine holding it")
    else:
        want_ref = f"plugin-v{pj}"
        if src.get("ref") != want_ref:
            fail.append(f"marketplace.json pins ref {src.get('ref')!r} but plugin.json is "
                        f"{pj} — the release commit must pin {want_ref!r}")
        if src.get("path") != "wellforge-plugin":
            fail.append(f"marketplace.json source path is {src.get('path')!r}, expected "
                        f"'wellforge-plugin'")

for p in glob.glob(f"{PLUGIN}/skills/*/SKILL.md"):
    fm = yaml.safe_load(open(p).read().split("---\n", 2)[1])
    n = len(fm.get("description", ""))
    if n > 1024:
        fail.append(f"skill `{fm['name']}` description is {n} chars (limit 1024)")

# Cross-skill references are relative markdown links, so they resolve for a human on GitHub
# and in an editor — not `[[wiki-links]]`, which look like links and are inert everywhere.
# Both halves are checked: no wiki-links come back, and every relative link has a real file
# behind it (in this layout AND in the adapters', which mirror it).
for p in glob.glob(f"{PLUGIN}/**/*.md", recursive=True):
    body = open(p).read()
    for link in re.findall(r"\[\[([a-z0-9-]+)\]\]", body):
        fail.append(f"{os.path.relpath(p, ROOT)}: [[{link}]] is an inert wiki-link — "
                    f"use a relative markdown link instead")
    for target in re.findall(r"\]\((\.\./[^)]*\.md)\)", body):
        resolved = os.path.normpath(os.path.join(os.path.dirname(p), target))
        if not os.path.exists(resolved):
            fail.append(f"{os.path.relpath(p, ROOT)}: link -> {target} resolves to nothing")

# ── 7. schema mirrors the skills ────────────────────────────────────────────────
# The skill is the authority; the schema must say the same thing. Edited apart, the machine
# would accept a status the documentation forbids (or refuse one it blesses), and every
# consumer of forge-state.py would inherit the discrepancy silently.
schema_path = f"{PLUGIN}/config/spec-frontmatter.schema.json"
if os.path.exists(schema_path):
    schema = json.load(open(schema_path))
    sd = open(f"{PLUGIN}/skills/spec-driven/SKILL.md").read()
    rt = open(f"{PLUGIN}/skills/rigor-tiers/SKILL.md").read()

    statuses = schema["$defs"]["status"]["enum"]
    # The lifecycle diagram in spec-driven is the source: every status must appear in it.
    # Pick the fenced block BY CONTENT — the first fence in the file is not the diagram,
    # and an index-based grab silently checks the wrong text.
    fences = sd.split("```")[1::2]
    diagram = next((f for f in fences if "draft" in f and "in-progress" in f), sd)
    for s in statuses:
        if s not in diagram:
            fail.append(f"schema status `{s}` is absent from the spec-driven lifecycle diagram")
    for s in ("draft", "approved", "in-progress", "done", "superseded", "archived"):
        if s not in statuses:
            fail.append(f"spec-driven documents status `{s}` but the schema's enum omits it")

    tiers = schema["$defs"]["rigor"]["enum"]
    for t in ("spike", "mvp", "production"):
        if t not in tiers:
            fail.append(f"rigor-tiers documents tier `{t}` but the schema's enum omits it")
        if f"`{t}`" not in rt:
            fail.append(f"schema tier `{t}` is not documented in the rigor-tiers skill")

# ── the run-trace schema version, stated in one place and quoted in many ────────────
# Four documents named a version and three were stale: implement/spike/orchestrate still
# said v2 and the evaluator said v1, while the observability skill — the authority — was
# already on v3. A producer writing `"schema": "wellforge-run/v2"` is not a cosmetic
# mismatch: the trace it writes claims to be a schema it is not, and a reader that one day
# drops v2 would drop live traces.
#
# The skill's heading is the single source. Everything else must agree, except the two
# places that legitimately name OLD versions: run-report.py's ACCEPTED_SCHEMAS (a reader
# must keep accepting the archive) and the migration notes (history).
_obs_path = os.path.join(PLUGIN, "skills", "observability", "SKILL.md")
_obs = open(_obs_path, encoding="utf-8").read()
_m = re.search(r"^## Semantic run trace — schema `(wellforge-run/v\d+)`", _obs, re.M)
if not _m:
    fail.append("observability/SKILL.md has no `## Semantic run trace — schema `wellforge-run/vN`` "
                "heading — the schema version has no single source")
else:
    current = _m.group(1)
    _EXEMPT = (
        os.path.join(PLUGIN, "scripts", "run-report.py"),      # must accept every old version
        os.path.join(PLUGIN, "scripts", "check-docs.py"),      # this check itself
    )
    for dirpath, dirnames, filenames in os.walk(PLUGIN):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "tests")]
        for fn in filenames:
            if not fn.endswith((".md", ".py", ".json", ".sh")):
                continue
            fp = os.path.join(dirpath, fn)
            if fp in _EXEMPT:
                continue
            try:
                body = open(fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for lineno, line in enumerate(body.splitlines(), 1):
                for found in re.findall(r"wellforge-run/v\d+", line):
                    if found != current:
                        rel = os.path.relpath(fp, ROOT)
                        fail.append(f"{rel}:{lineno} names `{found}` but the observability "
                                    f"skill's current schema is `{current}`")

# ── gates/README.md's pin numbers vs the workflows that actually pin them ───────────
# The README is where a human looks up what the gates run. It said osv-scanner v2.0.0 and
# semgrep 1.172.0 while the workflows pinned v2.5.1 and 1.173.0 — numbers that had drifted
# behind the thing they describe, which is the same failure class as the plugin version
# living in four files. A wrong pin in the README is worse than no pin: it is the number
# someone copies into a new gate.
_WORKFLOWS = os.path.join(ROOT, ".github", "workflows")
_readme_path = os.path.join(ROOT, "gates", "README.md")
if os.path.exists(_readme_path) and os.path.isdir(_WORKFLOWS):
    _readme = open(_readme_path, encoding="utf-8").read()
    _env = {}
    for wf in ("quality-node.yml", "quality-jvm.yml"):
        p = os.path.join(_WORKFLOWS, wf)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            m = re.match(r"\s*(SEMGREP_VERSION|OSV_SCANNER_VERSION):\s*(\S+)\s*$", line)
            if m:
                _env.setdefault(m.group(1), set()).add(m.group(2))

    for var, label in (("SEMGREP_VERSION", "semgrep"), ("OSV_SCANNER_VERSION", "osv-scanner")):
        vals = _env.get(var)
        if not vals:
            continue
        if len(vals) > 1:
            fail.append(f"the gate workflows pin different {label} versions: {sorted(vals)}")
            continue
        pinned = next(iter(vals))
        bare = pinned.lstrip("v")
        # Any OTHER version of this tool mentioned in the README is drift. Matching on the
        # tool name keeps this from tripping over unrelated numbers in the prose.
        for lineno, line in enumerate(_readme.splitlines(), 1):
            # TABLE ROWS ONLY. The prose deliberately names OLD versions — the section on
            # keeping the pin current cites semgrep 1.96.0 as the release that stopped
            # starting on newer runner Pythons, and that sentence is history, not a pin.
            # Flagging it would push someone to "fix" a worked example into nonsense.
            if not line.lstrip().startswith("|"):
                continue
            if label not in line.lower():
                continue
            for found in re.findall(rf"{label}[^0-9\n]{{0,4}}v?(\d+\.\d+\.\d+)", line, re.I):
                if found != bare:
                    fail.append(f"gates/README.md:{lineno} says {label} {found} but the gate "
                                f"workflows pin {pinned} — the README is the number people copy")

# ── the CLI's version lives in three files and a tag ────────────────────────────────
# Formula/wellforge.rb had no `version` line at all and its url still pointed at the
# TEMPLATE tag v0.9.0, so Homebrew guessed 0.9.0 while the script printed 1.4.0 — and the
# formula's own `test do` block compares the two. A brew user ran a CLI a year behind every
# report that named it current.
_cli_path = os.path.join(ROOT, "scripts", "wellforge")
_formula_path = os.path.join(ROOT, "Formula", "wellforge.rb")
cli_version = None
if os.path.exists(_cli_path):
    m = re.search(r'^WELLFORGE_CLI_VERSION="([0-9]+\.[0-9]+\.[0-9]+)"', open(_cli_path).read(), re.M)
    if m:
        cli_version = m.group(1)
    else:
        fail.append("scripts/wellforge has no WELLFORGE_CLI_VERSION — the CLI version has no source")

if cli_version and os.path.exists(_formula_path):
    ftext = open(_formula_path).read()
    # The URL's tag is what Homebrew derives the version FROM, so it is the thing to check.
    #
    # This used to demand an explicit `version` line on the theory that "a cli-vX.Y.Z tag is
    # not a shape Homebrew can parse". That was wrong, and `brew audit --strict` says so:
    # "`version 1.5.1` is redundant with version scanned from URL", with `brew info`
    # reporting a derived version of 1.5.1. The original bug was never a parsing failure —
    # the url simply pointed at the TEMPLATE tag v0.9.0, so brew parsed 0.9.0 perfectly well
    # from the wrong tag. Fixing the url fixed the version.
    um = re.search(r'archive/refs/tags/([^\s"]+)\.tar\.gz', ftext)
    if not um:
        fail.append("Formula/wellforge.rb has no recognisable archive url — nothing to derive "
                    "a version from")
    elif not um.group(1).startswith("cli-v"):
        fail.append(f"Formula/wellforge.rb url points at {um.group(1)!r}, which is not a cli-v "
                    f"tag — the CLI ships in its own series (docs/VERSIONING.md)")
    elif um.group(1) != f"cli-v{cli_version}":
        fail.append(f"Formula/wellforge.rb url names {um.group(1)} but scripts/wellforge is "
                    f"{cli_version} — brew derives the version from that url, and `brew test` "
                    f"asserts it against what the script prints")
    # An explicit `version` is allowed but must agree; `brew audit --strict` calls it
    # redundant, so the formula does not carry one.
    fm = re.search(r'^\s*version "([0-9]+\.[0-9]+\.[0-9]+)"', ftext, re.M)
    if fm and fm.group(1) != cli_version:
        fail.append(f"Formula/wellforge.rb pins version {fm.group(1)} but scripts/wellforge is "
                    f"{cli_version}")
    # The sha is a placeholder until the tag is pushed and release-cli.sh fills it in. That
    # is a WARNING, not a failure: it is a true statement about an unreleased formula, and
    # failing CI for it would block every unrelated change until someone cuts a release.
    # Needed by both branches below (placeholder and mismatch), so it is defined before
    # either. It used to live inside the placeholder branch, and the mismatch branch's
    # reference to it raised NameError — which the broad `except Exception` below then
    # reported as "offline or unreachable". A check that reassures you when its own code is
    # broken is worse than no check; that is the exact failure this rule exists to catch,
    # committed by the rule itself.
    fix = f"scripts/release-cli.sh {cli_version} --formula-only --execute"
    if re.search(r'sha256 "0{64}"', ftext):
        # WARN while the tag is unpushed — an unreleased formula is a true state and must
        # not block unrelated work. FAIL once the tag EXISTS on the remote, because from
        # that moment the tarball is fetchable, `release-cli.sh --formula-only` can fill
        # the hash in, and a placeholder left behind is simply a broken `brew install`
        # waiting for someone.
        import subprocess as _sp
        tag = f"cli-v{cli_version}"
        try:
            r = _sp.run(["git", "-C", ROOT, "ls-remote", "--tags", "origin",
                         f"refs/tags/{tag}"], capture_output=True, text=True, timeout=20)
            on_remote = (r.returncode == 0 and bool(r.stdout.strip()))
            reachable = (r.returncode == 0)
        except Exception:  # noqa: BLE001
            on_remote, reachable = False, False
        if on_remote:
            fail.append(f"Formula/wellforge.rb still carries a placeholder sha256 although "
                        f"{tag} is on the remote — run: {fix}")
        elif not reachable:
            print(f"⚠ Formula/wellforge.rb carries a placeholder sha256, and the remote could "
                  f"not be reached to see whether {tag} exists. If it does, run: {fix}",
                  file=sys.stderr)
        else:
            print(f"⚠ Formula/wellforge.rb carries a placeholder sha256 — {tag} is not pushed "
                  f"yet, so there is no tarball to hash. After pushing it, run: {fix}",
                  file=sys.stderr)
    else:
        # ── the third state: a sha that is PRESENT is not the same as a sha that is RIGHT ──
        # A wrong hash is worse than a placeholder. A placeholder announces itself — brew
        # refuses it loudly and this script says so. A plausible-looking wrong one passes
        # every check that only looks at the file, and fails later on someone else's
        # machine as "SHA256 mismatch", which reads like a corrupted download or a
        # compromised tarball rather than a release cut wrong. The only way to tell the two
        # apart is to fetch the tarball the url actually names and hash it.
        #
        # Verified with urllib + hashlib rather than `curl … | shasum -a 256`: same bytes,
        # same digest, but no dependency on which of curl/wget and shasum/sha256sum this
        # machine has, and a pipeline's exit status hides a failed download behind a
        # perfectly good hash of an error page.
        #
        # FAIL only on a definite mismatch. Anything that merely prevents the check —
        # offline, proxied, rate-limited, tag not pushed — is a WARNING: it is a statement
        # about the network, not about the formula, and must not fail an unrelated change.
        sm = re.search(r'sha256 "([0-9a-f]{64})"', ftext)
        um2 = re.search(r'url "(https://[^"]+\.tar\.gz)"', ftext)
        if os.environ.get("WELLFORGE_SKIP_SHA_VERIFY"):
            print("⚠ Formula sha256 not verified against the tarball "
                  "(WELLFORGE_SKIP_SHA_VERIFY is set)", file=sys.stderr)
        elif sm and um2:
            import hashlib
            import urllib.error
            import urllib.request
            declared, url = sm.group(1), um2.group(1)
            try:
                h = hashlib.sha256()
                with urllib.request.urlopen(url, timeout=60) as resp:
                    for chunk in iter(lambda: resp.read(1 << 16), b""):
                        h.update(chunk)
                actual = h.hexdigest()
                if actual != declared:
                    fail.append(
                        f"Formula/wellforge.rb's sha256 does not match the tarball it names.\n"
                        f"    url       {url}\n"
                        f"    declared  {declared}\n"
                        f"    actual    {actual}\n"
                        f"    Every `brew install` from this tap fails with a checksum "
                        f"mismatch. Re-cut it: {fix}")
            # NARROW, deliberately. These are the errors that mean "the network did not
            # cooperate"; anything else is a bug in this file and must crash loudly rather
            # than print a calm warning and exit 0.
            except (urllib.error.URLError, OSError, TimeoutError, ValueError) as e:
                print(f"⚠ could not verify Formula/wellforge.rb's sha256 against {url} "
                      f"(offline or unreachable: {type(e).__name__}) — the hash is present "
                      f"and well-formed, but nothing here has confirmed it is the right one",
                      file=sys.stderr)

# Tag agreement, only when tags are actually present — a shallow CI checkout has none, and
# "no tags" must not read as "the tags disagree".
if cli_version:
    try:
        import subprocess
        tags = subprocess.run(["git", "-C", ROOT, "tag", "-l", "cli-v*", "--sort=-v:refname"],
                              capture_output=True, text=True, timeout=10).stdout.split()
        if tags and tags[0] != f"cli-v{cli_version}":
            fail.append(f"newest cli tag is {tags[0]} but scripts/wellforge is {cli_version} — "
                        f"one of them was bumped without the other")
    except Exception:  # noqa: BLE001
        pass

# ── every npx-launched MCP server must name an EXACT version ────────────────────────
# `npx -y pkg@latest` (or with no version at all) resolves at launch, on the developer's
# machine, with network access and whatever the registry serves that minute. That is an
# unreviewed dependency running inside the session: a compromised or merely broken release
# reaches every teammate the moment it is published, and nothing in this repo records what
# they actually ran. The pin does not make the package trustworthy — it makes the version
# a reviewable fact and a bump an ordinary plugin patch release, which is what SECURITY.md
# promises.
#
# context-hub was already pinned (@0.1.4), so the pattern was known and the other two were
# simply missed. This is the check that notices.
_mcp = os.path.join(ROOT, "wellforge-plugin", ".mcp.json")
if os.path.exists(_mcp):
    try:
        with open(_mcp) as _f:
            _servers = json.load(_f).get("mcpServers", {})
    except (OSError, ValueError) as e:
        fail.append(f"wellforge-plugin/.mcp.json could not be read as JSON: {e}")
        _servers = {}
    for _name, _cfg in sorted(_servers.items()):
        if _cfg.get("command") != "npx":
            continue                      # http servers carry no version to pin
        _args = _cfg.get("args", [])
        # The package spec is the last argument that is not a flag and not the bare binary
        # name that follows `--package`. Handle both shapes actually in use:
        #   ["-y", "pkg@1.2.3"]                     and
        #   ["-y", "--package", "pkg@1.2.3", "bin"]
        if "--package" in _args:
            _i = _args.index("--package")
            _spec = _args[_i + 1] if _i + 1 < len(_args) else ""
        else:
            _spec = next((a for a in reversed(_args) if not a.startswith("-")), "")
        _at = _spec.rfind("@")
        _ver = _spec[_at + 1:] if _at > 0 else ""    # > 0 so a leading @scope is not the sep
        if not _ver:
            fail.append(f".mcp.json server '{_name}' runs `npx {_spec}` with NO version — it "
                        f"resolves at launch to whatever the registry serves. Pin it to an "
                        f"exact version (see SECURITY.md, 'MCP servers').")
        elif _ver in ("latest", "next", "beta", "canary") or not _ver[0].isdigit():
            fail.append(f".mcp.json server '{_name}' is pinned to '{_ver}', which is a moving "
                        f"tag, not a version. Pin an exact version (see SECURITY.md).")

# ── no document may claim a version that does not exist yet ─────────────────────────
# The brief for this check asked that EVERY plugin version mention equal plugin.json. It
# cannot: CLAUDE.md legitimately cites plugin 2.26.0 and 2.27.0 as the releases that shipped
# Phases 16 and 17, and rewriting those to today's number would turn a changelog into a lie.
# The rule that IS enforceable: nothing may claim a version NEWER than the files define
# (that version does not exist), and the single designated current-state line must match
# exactly. Everything older than the current version is history and is left alone.
def _tuple(v):
    return tuple(int(x) for x in v.split("."))


_docs = [("README.md", os.path.join(ROOT, "README.md")),
         ("CLAUDE.md", os.path.join(ROOT, "CLAUDE.md")),
         ("docs/INSTALLATION.md", os.path.join(ROOT, "docs", "INSTALLATION.md"))]
for label, path in _docs:
    if not os.path.exists(path):
        continue
    body = open(path, encoding="utf-8").read()
    for lineno, line in enumerate(body.splitlines(), 1):
        for found in re.findall(r"plugin[ -]`?v?([0-9]+\.[0-9]+\.[0-9]+)`?", line):
            if _tuple(found) > _tuple(pj):
                fail.append(f"{label}:{lineno} names plugin {found}, which is newer than "
                            f"plugin.json ({pj}) — that release does not exist")
        if cli_version:
            for found in re.findall(r"(?:CLI|cli)[ -]`?v?([0-9]+\.[0-9]+\.[0-9]+)`?", line):
                if _tuple(found) > _tuple(cli_version):
                    fail.append(f"{label}:{lineno} names CLI {found}, newer than "
                                f"scripts/wellforge ({cli_version}) — that release does not exist")

# The designated current-state line, asserted exactly.
_cl = open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8").read()
_cur = [l for l in _cl.splitlines() if "Latest tags:" in l]
if not _cur:
    fail.append("CLAUDE.md no longer has a `Latest tags:` line — the current-state check "
                "has nothing to assert against")
else:
    # The statement spans a few wrapped lines; take the paragraph.
    _idx = _cl.splitlines().index(_cur[0])
    _para = "\n".join(_cl.splitlines()[_idx:_idx + 6])
    # EVERY version in this paragraph must be the current one. Requiring merely that the
    # current version appears somewhere is not enough: the paragraph names each series
    # twice (as a tag and as a bare version), so one of the two could go stale while the
    # other satisfied the check — measured, that is exactly what slipped through.
    for found in re.findall(r"plugin[ -]`?v?([0-9]+\.[0-9]+\.[0-9]+)`?", _para):
        if found != pj:
            fail.append(f"CLAUDE.md's `Latest tags` paragraph names plugin {found} but "
                        f"plugin.json is {pj} — the one paragraph that states current "
                        f"versions has a stale mention")
    if cli_version:
        for found in re.findall(r"(?:CLI|cli)[ -]`?v?([0-9]+\.[0-9]+\.[0-9]+)`?", _para):
            if found != cli_version:
                fail.append(f"CLAUDE.md's `Latest tags` paragraph names CLI {found} but "
                            f"scripts/wellforge is {cli_version}")
    if f"plugin `{pj}`" not in _para and f"plugin-v{pj}" not in _para:
        fail.append(f"CLAUDE.md's `Latest tags` paragraph does not name plugin {pj} "
                    f"(plugin.json) — the one line that states current versions is stale")
    if cli_version and f"cli-v{cli_version}" not in _para:
        fail.append(f"CLAUDE.md's `Latest tags` paragraph does not name cli-v{cli_version} "
                    f"(scripts/wellforge) — the one line that states current versions is stale")

if fail:
    print("✗ docs drift:")
    for f in fail:
        print(f"    {f}")
    sys.exit(1)
print(f"✓ docs consistent — {len(cmds)} commands, {len(skills)} skills, "
      f"{len(mcp.get('mcpServers', mcp))} MCP servers listed; version {pj} in sync "
      f"(plugin.json = CLAUDE.md = marketplace.json = ref plugin-v{pj})")
