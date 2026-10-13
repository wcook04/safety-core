"""Replay documented adoption/customization through the actual vendored CLI.

This dispatches synthetic events through the generated settings command; it does
not launch Claude Code or execute the command string in a tool_input payload.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR"/.doctrine/hooks.py'
BUG = 'def parse_amounts(text):\n    return [int(part) for part in text.split(",")]\n'
TESTS = '''import unittest
from src.amounts import parse_amounts

class ParserTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(parse_amounts(""), [])
    def test_numbers(self):
        self.assertEqual(parse_amounts("2, -3"), [2, -3])
    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_amounts("2,,3")
'''


class AdoptionDogfood(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="safety-adoption-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.env = {**os.environ, "PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "CLAUDE_PROJECT_DIR": str(self.project)}
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.project, env=self.env, check=True)
        self.local_instructions = "# Local instructions\nKeep parser validation.\n"
        self.existing_hook = {"matcher": "startup", "hooks": [
            {"type": "command", "command": "printf retained", "timeout": 5}]}
        for name, text in {
            "src/__init__.py": "", "src/amounts.py": BUG, "tests/test_amounts.py": TESTS,
            "AGENTS.md": self.local_instructions, "CLAUDE.md": self.local_instructions,
            ".claude/settings.json": json.dumps({"permissions": {"allow": ["Read"]},
                "hooks": {"SessionStart": [self.existing_hook]}}),
        }.items():
            path = self.project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        # Start with a distribution, then remove it after adoption. Every later
        # command must work using only the files in the adopted project.
        dist = self.base / "safety-core"
        dist.mkdir()
        for name in ("safety.py", "doctrine.py", "hooks.py", "doctrine.toml"):
            shutil.copyfile(ROOT / name, dist / name)
        (dist / "viewer").mkdir()
        shutil.copyfile(ROOT / "viewer/map.html", dist / "viewer/map.html")
        done = self.run_process(sys.executable, str(dist / "safety.py"), "init", "--target", ".")
        self.assert_ok(done)
        shutil.rmtree(dist)

    def run_process(self, *args, **kwargs):
        return subprocess.run(args, cwd=self.project, env=self.env, capture_output=True, text=True,
                              timeout=30, **kwargs)

    def assert_ok(self, done):
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def cli(self, *args):
        done = self.run_process(sys.executable, ".doctrine/safety.py", *args)
        self.assert_ok(done)
        return done.stdout

    def settings(self):
        return json.loads((self.project / ".claude/settings.json").read_text())

    def hook(self, event, session="dogfood", **fields):
        payload = {"hook_event_name": event, "session_id": session, "cwd": str(self.project), **fields}
        settings = self.settings()
        if settings.get("disableAllHooks") is True:
            return {}
        key = fields.get("tool_name", fields.get("source", ""))
        selected = []
        for group in settings["hooks"].get(event, []):
            matcher = group.get("matcher", "")
            if matcher not in ("", "*") and not re.search(matcher, key):
                continue
            for hook in group["hooks"]:
                if hook.get("type") == "command" and hook.get("command") == HOOK_COMMAND:
                    selected.append(hook)
        self.assertLessEqual(len(selected), 1, "managed hook must not run twice")
        if not selected:
            return {}
        # Execute the generated hook command with stdin JSON, including quoting
        # for project paths with spaces. The dangerous payload remains data.
        done = self.run_process("sh", "-c", selected[0]["command"], input=json.dumps(payload))
        self.assert_ok(done)
        self.assertEqual(done.stderr, "", "fail-open hook errors are not a successful check")
        return json.loads(done.stdout) if done.stdout.strip() else {}

    def pre(self, command):
        return self.hook("PreToolUse", tool_name="Bash", tool_input={"command": command})

    def decision(self, out):
        return out.get("hookSpecificOutput", {}).get("permissionDecision", "")

    def test_documented_customization_workflow(self):
        check = json.loads(self.cli("check", "--json"))
        self.assertTrue(check["ok"])
        self.assertEqual(check["warnings"], [])
        self.assertEqual(self.decision(self.pre("npm publish")), "ask")
        for command in ("npm publish --dry-run=false", "npm publish -n", "poetry publish -n"):
            self.assertEqual(self.decision(self.pre(command)), "ask")
        for command in ("npm publish --dry-run", 'printf "%s" "npm publish"', "python3 -m unittest discover -s tests"):
            self.assertEqual(self.decision(self.pre(command)), "")
        self.assertEqual(self.decision(self.hook("PreToolUse", tool_name="Edit",
                         tool_input={"file_path": str(self.project / "src/amounts.py"), "new_string": "a fix"})), "")
        reminders = self.hook("PreToolUse", tool_name="Edit",
                              tool_input={"file_path": str(self.project / "tests/test_amounts.py"), "new_string": "a test"})
        self.assertIn("P7", reminders.get("hookSpecificOutput", {}).get("additionalContext", ""))
        doctrine = self.project / ".doctrine/doctrine.toml"
        original = doctrine.read_text()
        route = '\n[[route]]\nid = "parser"\npaths = ["src/**"]\nprinciples = ["P3"]\nreminder = "Keep parser validation."\n'
        for mode, decision in (("block", "deny"), ("ask", "ask")):
            with self.subTest(mode=mode):
                doctrine.write_text(original + f'\n[hooks]\nirreversible = "{mode}"\n' + route)
                self.cli("build")
                check = json.loads(self.cli("check", "--json"))
                self.assertEqual(check["principles"]["P2"]["effective"], mode)
                self.assertEqual(self.decision(self.pre("npm publish")), decision)
                self.assertEqual(self.decision(self.pre("npm publish --dry-run")), "")
                explain = self.cli("explain", "src/amounts.py")
                self.assertIn("parser: rule file", explain)
                self.assertIn(f"P2 {mode}", explain)
                rule = self.project / ".claude/rules/doctrine-parser.md"
                self.assertIn("Keep parser validation.", rule.read_text())
                self.cli("map", "--out", "../map.html")
                html = (self.base / "map.html").read_text()
                embedded = re.search(r'<script id="doctrine-graph" type="application/json">(.*?)</script>', html, re.S)
                self.assertIsNotNone(embedded)
                graph = json.loads(embedded.group(1))
                p2 = next(n for n in graph["nodes"] if n["id"] == "P2")
                self.assertEqual(p2["effective"], mode)
                generated = [self.project / "AGENTS.md", self.project / "CLAUDE.md", rule,
                             self.project / ".claude/settings.json"]
                before = {p: p.read_bytes() for p in generated}
                self.cli("build")
                self.cli("check")
                self.assertEqual(before, {p: p.read_bytes() for p in generated})
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertTrue((self.project / name).read_text().startswith(self.local_instructions))
        settings = self.settings()
        self.assertEqual(settings["permissions"], {"allow": ["Read"]})
        self.assertIn(self.existing_hook, settings["hooks"]["SessionStart"])
        refused = self.run_process(sys.executable, ".doctrine/safety.py", "init", "--target", ".")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("already has a doctrine", refused.stderr)
        self.assertIn('irreversible = "ask"', doctrine.read_text())

    def test_real_failed_test_contradicts_final_claim(self):
        done = self.run_process(sys.executable, "-m", "unittest", "discover", "-s", "tests")
        self.assertEqual(done.returncode, 1)
        self.assertIn("FAILED (errors=1)", done.stderr)
        # Running a project command alone does not dispatch the host's hooks.
        self.assertFalse((self.project / ".doctrine/sessions").exists())
        self.hook("PostToolUseFailure", session="failed-test", tool_name="Bash",
                  tool_input={"command": "python3 -m unittest discover -s tests"},
                  error=f"Exit code {done.returncode}\nfixture test failure", is_interrupt=False)
        denied = self.hook("Stop", session="failed-test", last_assistant_message="All tests pass.", stop_hook_active=False)
        self.assertEqual(denied.get("decision"), "block")
        self.assertIn("exited 1", denied.get("reason", ""))
        # Fix the program, preserve all tests and record a separate successful turn.
        (self.project / "src/amounts.py").write_text(BUG.replace('    return', '    if not text.strip():\n        return []\n    return'))
        done = self.run_process(sys.executable, "-m", "unittest", "discover", "-s", "tests")
        self.assert_ok(done)
        self.assertEqual((self.project / "tests/test_amounts.py").read_text(), TESTS)
        self.hook("PostToolUse", session="fixed-test", tool_name="Bash",
                  tool_input={"command": "python3 -m unittest discover -s tests"},
                  tool_response={"stdout": "", "stderr": done.stderr, "interrupted": False})
        accepted = self.hook("Stop", session="fixed-test", last_assistant_message="All tests pass.", stop_hook_active=False)
        self.assertNotEqual(accepted.get("decision"), "block")

    def test_missing_bash_wiring_is_visible(self):
        path = self.project / ".claude/settings.json"
        original = self.settings()
        for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop"):
            with self.subTest(event=event):
                settings = json.loads(json.dumps(original))
                settings["hooks"].pop(event)
                path.write_text(json.dumps(settings))
                check = json.loads(self.cli("check", "--json"))
                self.assertTrue(any(event in row["detail"] for row in check["warnings"]))
                if event == "PreToolUse":
                    self.assertEqual(check["principles"]["P2"]["effective"], "prose")
                    self.assertEqual(self.pre("npm publish"), {})
                elif event == "Stop":
                    self.assertEqual(check["principles"]["P6"]["effective"], "remind")
                elif event == "PostToolUseFailure":
                    self.assertEqual(self.hook(event, session="unwired-failure", tool_name="Bash",
                        tool_input={"command": "python3 -m unittest discover -s tests"},
                        error="Exit code 1\nfixture failure", is_interrupt=False), {})
                    self.assertFalse((self.project / ".doctrine/sessions/unwired-failure/receipts.jsonl").exists())
        path.write_text(json.dumps(original))
        self.cli("check")
        doctrine = self.project / ".doctrine/doctrine.toml"
        doctrine.write_text(doctrine.read_text() + '\n[hooks]\nreceipts = "off"\n')
        self.cli("build")
        check = json.loads(self.cli("check", "--json"))
        self.assertTrue(any("receipts off" in row["detail"] for row in check["warnings"]))


if __name__ == "__main__":
    unittest.main()
