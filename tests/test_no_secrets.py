"""No Cortex credentials in the repository, ever again.

This repository shipped a real Client ID and Secret twice over: hard-coded in
cortex.py, where it also overrode whatever the user typed, and committed in
config.json. Both are gone; this test is what stops a third time.
"""
import json
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A Cortex client id is 40 characters and a secret is 128, both from the same
# alphabet, so anything that long sitting in a source file is assumed to be one.
LONG_TOKEN = re.compile(r"[A-Za-z0-9]{40,}")

# Things that are legitimately long and not secrets.
ALLOWED = (
    "abcdefghijklmnopqrstuvwxyz",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
)


def tracked_files():
    """Ask git, so the test covers exactly what would be published."""
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


class NoCommittedSecrets(unittest.TestCase):
    def test_runtime_settings_are_not_tracked(self):
        tracked = tracked_files()
        self.assertNotIn("config.json", tracked,
                         "config.json holds Cortex credentials and must stay untracked")
        self.assertNotIn("phrases.json", tracked)

    def test_example_config_has_no_values(self):
        with open(os.path.join(ROOT, "config.example.json"), encoding="utf-8") as f:
            example = json.load(f)
        self.assertEqual(example["cortex_client_id"], "")
        self.assertEqual(example["cortex_client_secret"], "")

    def test_no_long_tokens_in_tracked_sources(self):
        offenders = []
        for rel in tracked_files():
            if not rel.endswith((".py", ".json", ".md", ".iss", ".spec", ".yml")):
                continue
            path = os.path.join(ROOT, rel)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            for match in LONG_TOKEN.findall(text):
                if match in ALLOWED:
                    continue
                offenders.append(f"{rel}: {match[:16]}…")
        self.assertEqual(offenders, [], "possible credential in a tracked file")

    def test_cortex_does_not_override_the_caller(self):
        """The constructor must use the credentials it is given."""
        with open(os.path.join(ROOT, "cortex.py"), encoding="utf-8") as f:
            source = f.read()
        head = source[source.index("def __init__(self, client_id"):][:600]
        self.assertNotRegex(head, r"client_id\s*=\s*['\"][A-Za-z0-9]")
        self.assertNotRegex(head, r"client_secret\s*=\s*['\"][A-Za-z0-9]")


if __name__ == "__main__":
    unittest.main()
