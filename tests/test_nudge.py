"""The compact nudge must stay display only: it may draw above the prompt and
show a toast, and must never put anything in front of the model. This reads
the plugin's source, and (when the claude CLI is installed) what Claude Code's
own validator says the plugin hooks and calls."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from support import ROOT

PLUGIN = ROOT / "plugins" / "compact-nudge"
# hooks and calls that reach the model's context or the transcript
TO_THE_MODEL = ("prompt.context", "prompt.attachment", "prompt.section", "prompt.submit",
                "session.append", "additionalContext")
HOOKS_ALLOWED = {"prompt.submit", "tool.call{tool=Bash}", "turn.complete", "ui.render{component=AbovePrompt}"}
CALLS_ALLOWED = {"$.session.usage", "$.state.get", "$.state.set", "$.ui.resolve", "$.ui.toast"}


def source():
    return "\n".join(p.read_text() for p in (PLUGIN / "hooks").glob("*.ts*") if ".test." not in p.name)


class DisplayOnly(unittest.TestCase):
    def test_source_never_names_a_way_to_the_model(self):
        src = source()
        for name in TO_THE_MODEL:
            with self.subTest(name=name):
                if name == "prompt.submit":  # listening is fine; calling $.prompt.submit is not
                    self.assertNotIn("$.prompt.submit", src)
                else:
                    self.assertNotIn(name, src)

    def test_turn_complete_returns_what_it_was_given(self):
        # a turn.complete hook that returns { text } would print under the answer
        body = re.search(r"on\('turn\.complete'.*?\n  \}\)", source(), re.S).group(0)
        self.assertIn("return done", body)
        self.assertNotRegex(body, r"text\s*:")


@unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
class Validator(unittest.TestCase):
    def setUp(self):
        # claude writes ~/.claude.json and backups as it runs: give it a home of its own
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        self.env = {**os.environ, "HOME": home.name}
        out = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True,
                             timeout=120, env=self.env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.report = out.stdout + out.stderr

    def listed(self, what):
        found = re.search(rf"register\.tsx {what}: (.+)", self.report)
        self.assertIsNotNone(found, self.report)
        return {x.strip() for x in found.group(1).split(", ")}

    def test_hooks_are_only_the_ones_it_needs(self):
        self.assertEqual(self.listed("hooks"), HOOKS_ALLOWED)

    def test_calls_are_only_reading_usage_state_and_drawing(self):
        self.assertEqual(self.listed("calls"), CALLS_ALLOWED)

    def test_the_plugins_own_tests_pass(self):
        out = subprocess.run(["claude", "plugin", "test", str(PLUGIN)], capture_output=True, text=True,
                             timeout=300, env=self.env)
        self.assertEqual(out.returncode, 0, out.stdout[-2000:] + out.stderr[-2000:])
        self.assertRegex(out.stdout + out.stderr, r"\b0 fail\b")


if __name__ == "__main__":
    unittest.main()
