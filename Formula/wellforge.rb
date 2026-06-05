# Homebrew formula — the wellforge repo doubles as a tap:
#
#   brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
#   brew install --HEAD matteocodogno/wellforge/wellforge
#   wellforge setup
#
# Head-only while pre-1.0; pin a `url ... tag:` stanza at the v1.0.0 cut.
class Wellforge < Formula
  desc "welld internal platform: reproducible, AI-assisted project setup"
  homepage "https://github.com/matteocodogno/wellforge"
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
      Finish the setup (clones the wellforge repo to ~/.wellforge, checks the
      toolchain, registers the Claude Code plugin):

        wellforge setup

      Anytime health check:  wellforge doctor
      Stay current:          wellforge update
    EOS
  end

  test do
    assert_match "doctor", shell_output("#{bin}/wellforge help")
  end
end
