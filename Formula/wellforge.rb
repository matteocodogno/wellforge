# Homebrew formula — the wellforge repo doubles as a tap:
#
#   brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
#   brew install matteocodogno/wellforge/wellforge
#   wellforge setup
#
# Versioned tarball install (NOT head-only): brew's git-based HEAD staging failed
# inside the install sandbox on some machines ("no time information in ''"), and
# plain tarballs also give normal `brew upgrade` semantics.
#
# THE CLI HAS ITS OWN TAG SERIES: `cli-vX.Y.Z`, not the template's `vX.Y.Z`. It used to
# follow the template, so a CLI fix could only ship with a template release — and since
# docs/VERSIONING.md requires a template release to carry a template change, CLI fixes
# simply did not ship. Do not bump url/sha256 by hand:
#
#   scripts/release-cli.sh patch --execute
#
# That script is the release: it bumps WELLFORGE_CLI_VERSION in scripts/wellforge, tags
# cli-vX.Y.Z, pushes, and only THEN fetches the tarball to compute its sha256 — GitHub
# generates that archive and it is not reproducible locally (measured: for v0.9.0, a local
# `git archive` of the same tree hashes to 746cc34f…, the formula pins b61eafcb…).
#
# `version` is stated explicitly rather than parsed out of the url, so the number cannot
# drift from what the script prints and stays monotonic across the change of series.
class Wellforge < Formula
  desc "Reproducible, AI-assisted project setup platform"
  homepage "https://github.com/matteocodogno/wellforge"
  url "https://github.com/matteocodogno/wellforge/archive/refs/tags/cli-v1.5.1.tar.gz"
  # PLACEHOLDER — not a real hash. The tarball does not exist until cli-v1.5.1 is pushed, and
  # GitHub's generated archive is not byte-reproducible locally (release-cli.sh's header
  # records the measurement). Fill it with:
  #     scripts/release-cli.sh 1.5.1 --formula-only --execute
  # An all-zero sha fails `brew install` loudly. The previous value was real and pinned the
  # TEMPLATE tag v0.9.0, so brew installed a year-old CLI successfully and only `brew test`
  # noticed — silent-wrong, which is the worse of the two.
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  # EXPLICIT version, because the tag is `cli-vX.Y.Z` and Homebrew cannot parse a version
  # out of that shape. The `test do` block asserts `version` against what the script
  # prints; with no version line brew guessed 0.9.0 from the old url and compared it to
  # "wellforge 1.5.1".
  version "1.5.1"
  license "MIT"
  head "https://github.com/matteocodogno/wellforge.git", branch: "main"

  depends_on "gh"
  depends_on "jq"
  depends_on "mise"
  depends_on "uv"

  def install
    bin.install "scripts/wellforge"
  end

  def caveats
    <<~EOS
      Finish the setup (clones the wellforge repo — default ~/.ai/wellforge,
      asked interactively — checks the toolchain, registers the Claude Code
      plugin):

        wellforge setup

      Anytime health check:  wellforge doctor
      Stay current:          wellforge update  (checkout) · brew upgrade  (this CLI)
    EOS
  end

  test do
    assert_match "doctor", shell_output("#{bin}/wellforge help")

    # The CLI's version is the WELLFORGE_CLI_VERSION constant inside the script, not this
    # formula and not the Cellar path. Asserting they agree is what catches a release that
    # bumped one and forgot the other — the failure mode that let brew users run the CLI
    # as it stood at v0.9.0 while every report called it current.
    assert_match version.to_s, shell_output("#{bin}/wellforge version")

    # The error model, verified through packaging rather than only in the repo's own
    # suite. `doctor` on a machine with no checkout is the first thing a new teammate
    # runs, and it used to die mid-report at exit 2 with no summary and no advice. It must
    # print the whole report and exit 1: a complete failure, not a crash.
    report = shell_output("HOME=#{testpath} #{bin}/wellforge doctor 2>&1", 1)
    assert_match "check(s) failed", report
    assert_match "wellforge setup", report

    # A typo must not look like success. `wellforge dcotor` exited 0 for a long time, so
    # nothing wrapping this script could tell the difference.
    shell_output("HOME=#{testpath} #{bin}/wellforge notacommand 2>&1", 1)
  end
end
