"""init: adopt the reference doctrine, keep the routes this repository needs, wire the hooks."""

from __future__ import annotations

import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from doctrine_testkit import DEMO_FILES, FAKE_HOOKS, REFERENCE, ROOT, RepoTestCase, doctrine


class Init(RepoTestCase):
    def setUp(self):
        # A stand-in for the folder doctrine.py runs from: the reference doctrine, this
        # doctrine.py, a hooks.py with a literal CHECKS dict and a viewer.
        self.dist = Path(tempfile.mkdtemp(prefix="doctrine-dist-")).resolve()
        self.addCleanup(shutil.rmtree, self.dist, ignore_errors=True)
        shutil.copyfile(REFERENCE, self.dist / "doctrine.toml")
        shutil.copyfile(ROOT / "doctrine.py", self.dist / "doctrine.py")
        (self.dist / "hooks.py").write_text(FAKE_HOOKS)
        (self.dist / "map.html").write_text('<html><head></head><body><script id="doctrine-graph" type="application/json"></script></body></html>')
        self.addCleanup(setattr, doctrine, "HERE", doctrine.HERE)
        doctrine.HERE = self.dist

    def init(self, files, settings=None):
        root = self.make_repo(files, doctrine_text=None, hooks=None)
        if settings is not None:
            (root / ".claude").mkdir()
            (root / ".claude" / "settings.json").write_text(json.dumps(settings, indent=4))
        code, out, err = self.run_cli(root, "init", "--target", str(root))
        self.assertEqual(code, 0, out + err)
        return root, out

    def test_init_adopts_and_trims_the_reference_doctrine(self):
        root, out = self.init(DEMO_FILES)
        for name in ("doctrine.toml", "doctrine.py", "hooks.py", "map.html", ".gitignore", "graph.json"):
            self.assertTrue((root / ".doctrine" / name).is_file(), name)
        d = doctrine.load(root / ".doctrine" / "doctrine.toml")
        self.assertEqual(sorted(d.routes), ["agent-rules", "dependencies", "docs", "migrations", "tests"])
        self.assertIn("routes dropped (no matching files): ci, infrastructure, secrets, release", out)
        text = (root / ".doctrine" / "doctrine.toml").read_text()
        self.assertIn("# ---------------------------------------------------------------- routes", text, "comments survive")
        self.assertIn("@AGENTS.md", (root / "CLAUDE.md").read_text())
        self.assertTrue((root / ".claude" / "rules" / "doctrine-migrations.md").is_file())
        code, out, _ = self.run_cli(root, "check")
        self.assertEqual(code, 0, out)
        self.assertNotIn("hooks_unwired", out)

    def test_source_viewer_is_installed_at_the_compatible_destination(self):
        (self.dist / "viewer").mkdir()
        source = self.dist / "viewer" / "map.html"
        source.write_text("<html>source viewer</html>")
        root, _ = self.init(DEMO_FILES)
        self.assertEqual((root / ".doctrine" / "map.html").read_text(), source.read_text())
        self.assertFalse((root / ".doctrine" / "viewer").exists())
        self.assertEqual(doctrine.find_viewer(root), root / ".doctrine" / "map.html")
        (root / ".doctrine" / "map.html").unlink()
        self.assertEqual(doctrine.find_viewer(root), source)
        source.unlink()
        self.assertEqual(doctrine.find_viewer(root), self.dist / "map.html")

    def test_a_principle_whose_only_route_was_dropped_falls_back_to_prose(self):
        files = dict(DEMO_FILES)
        files.pop("tests/orders.test.js")
        root, _ = self.init(files)
        raw = tomllib.loads((root / ".doctrine" / "doctrine.toml").read_text())
        p7 = next(p for p in raw["principle"] if p["id"] == "P7")
        self.assertEqual((p7["enforcement"], p7["enforced_by"]), ("prose", []))
        self.assertIn('enforcement = "prose"  # was "remind"; route tests matches no file here',
                      (root / ".doctrine" / "doctrine.toml").read_text())
        p6 = next(p for p in raw["principle"] if p["id"] == "P6")
        self.assertEqual(p6["enforced_by"], ["stop:claims#unsupported_claim"], "other refs are untouched")
        self.assertEqual(self.run_cli(root, "check")[0], 0)

    def test_wiring_merges_into_existing_settings(self):
        mine = {"permissions": {"allow": ["Bash(npm test)"]},
                "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "dcg"}]}]}}
        root, out = self.init(DEMO_FILES, settings=mine)
        settings = json.loads((root / ".claude" / "settings.json").read_text())
        self.assertEqual(settings["permissions"], mine["permissions"])
        pre = settings["hooks"]["PreToolUse"]
        self.assertEqual(pre[0], mine["hooks"]["PreToolUse"][0], "existing hooks stay first and unchanged")
        self.assertEqual(pre[1]["hooks"][0]["command"], doctrine.HOOK_COMMAND)
        self.assertEqual(set(settings["hooks"]), {"PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop", "SessionStart"})
        self.assertEqual(settings["hooks"]["SessionStart"][0]["matcher"], "startup|clear|compact")
        self.assertNotIn("matcher", settings["hooks"]["Stop"][0])
        self.assertFalse(doctrine.wire_hooks(root), "wiring twice changes nothing")
        self.assertIn("hooks: wired in .claude/settings.json", out)

    def test_init_refuses_to_replace_a_doctrine(self):
        root, _ = self.init(DEMO_FILES)
        code, _, err = self.run_cli(root, "init", "--target", str(root))
        self.assertEqual(code, 2)
        self.assertIn("already has a doctrine", err)
        code, _, _ = self.run_cli(root, "init", "--target", str(root), "--force")
        self.assertEqual(code, 0)

    def test_the_plugin_wires_the_same_events_as_init(self):
        wiring = doctrine.read_literal(ROOT / "hooks.py", "WIRING") or doctrine.WIRING
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "safety-core")
        hooks_file = ROOT / "hooks" / "hooks.json"
        if hooks_file.exists():  # Claude Code merges both, so only one may wire the hooks
            self.assertNotIn("hooks", manifest)
            hooks = json.loads(hooks_file.read_text())["hooks"]
        else:
            hooks = manifest["hooks"]
        self.assertEqual(set(hooks), set(wiring))
        for event, (matcher, timeout) in wiring.items():
            group = hooks[event][0]
            self.assertEqual(group.get("matcher", ""), matcher)
            self.assertEqual(group["hooks"][0]["timeout"], timeout)
            self.assertIn("${CLAUDE_PLUGIN_ROOT}", group["hooks"][0]["command"])
            self.assertIn("hooks.py", group["hooks"][0]["command"])

    def test_broken_settings_are_left_alone(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=None, hooks=None)
        (root / ".claude").mkdir()
        (root / ".claude" / "settings.json").write_text("{ not json")
        code, _, err = self.run_cli(root, "init", "--target", str(root))
        self.assertEqual(code, 2)
        self.assertIn("settings.json", err)
        self.assertEqual((root / ".claude" / "settings.json").read_text(), "{ not json")


if __name__ == "__main__":
    unittest.main()
