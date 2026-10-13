"""The docs, checked as if a reader followed them: every shell command in a
```sh block is run, or listed below with the reason it isn't, every link and
#anchor resolves, and the JSON examples parse.

A new command in the docs fails here until it's added to COMMANDS."""
import json
import os
import re
import subprocess
import tempfile
import unittest

from support import ROOT
from test_hygiene import files

# Each documented command, as written minus its comment, and how it's checked:
# ("run", folder) in an empty home folder, or ("skip", why).
COMMANDS = {
    "make test": ("skip", "this is the suite that is running"),
    "claude plugin test plugins/compact-nudge": ("skip", "test_nudge.py runs it"),
    "claude plugin validate plugins/compact-nudge": ("skip", "test_nudge.py runs it"),
    "python3 replay.py": ("run", ROOT / "plugins/compact-nudge/replay"),
}

FENCE = re.compile(r"^```(\w*)\n(.*?)^```", re.S | re.M)
COMMENT = re.compile(r"\s+#\s.*$")
HEADING = re.compile(r"^#+ (.+)$", re.M)
LINK = re.compile(r"\]\(([^)\s]+)\)")


def docs():
    return [(path, rel) for path, rel in files() if path.suffix == ".md"]


def blocks(lang):
    """(file, block text) for every fenced block in `lang` across the docs."""
    return [(rel, text) for path, rel in docs() for kind, text in FENCE.findall(path.read_text()) if kind == lang]


def anchor(heading):
    """GitHub's id for a heading: lower case, punctuation dropped, spaces to dashes."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


class DocumentedCommands(unittest.TestCase):
    def test_every_command_is_run_or_says_why_not(self):
        found = {" ".join(COMMENT.sub("", line).split())
                 for _, text in blocks("sh") for line in text.splitlines() if line.strip()}
        self.assertEqual(sorted(found - set(COMMANDS)), [], "new commands in the docs: add them to COMMANDS")
        self.assertEqual(sorted(set(COMMANDS) - found), [], "COMMANDS lists commands the docs no longer have")

    def test_commands_run_without_errors(self):
        for command, (how, where) in COMMANDS.items():
            if how != "run":
                continue
            with self.subTest(command=command), tempfile.TemporaryDirectory() as home:
                out = subprocess.run(["bash", "-c", command], cwd=where, capture_output=True, text=True,
                                     timeout=60, env={**os.environ, "HOME": home})
                self.assertEqual(out.returncode, 0, out.stderr[-2000:])
                self.assertNotIn("Traceback", out.stdout + out.stderr)


class DocumentedExamples(unittest.TestCase):
    def test_json_examples_parse(self):
        for rel, text in blocks("json"):
            with self.subTest(doc=str(rel), start=text[:40]):
                json.loads(text)

    def test_every_link_and_anchor_resolves(self):
        for path, rel in docs():
            text = FENCE.sub("", path.read_text())
            for target in LINK.findall(text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                file, _, frag = target.partition("#")
                dest = (path.parent / file).resolve() if file else path
                with self.subTest(doc=str(rel), link=target):
                    self.assertTrue(dest.exists(), f"{dest} doesn't exist")
                    if frag:
                        self.assertIn(frag, {anchor(h) for h in HEADING.findall(FENCE.sub("", dest.read_text()))})


if __name__ == "__main__":
    unittest.main()
