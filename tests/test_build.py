"""build: writes every projection and the graph, idempotently, without touching user text."""

from __future__ import annotations

import json
import os
import re
import unittest

from doctrine_testkit import DEMO_FILES, MINI, REFERENCE, RepoTestCase, doctrine


def snapshot(root):
    """Every file under root (except the graph, which carries a timestamp) with its bytes and mtime."""
    out = {}
    for folder, _, names in os.walk(root):
        for name in names:
            path = os.path.join(folder, name)
            if not path.endswith("graph.json"):
                with open(path, "rb") as fh:
                    out[os.path.relpath(path, root)] = (fh.read(), os.stat(path).st_mtime_ns)
    return out


class Build(RepoTestCase):
    def test_build_writes_every_projection_and_the_graph(self):
        root = self.make_repo(DEMO_FILES)
        out = self.build(root)
        self.assertIn("AGENTS.md", out)
        for rel in ("AGENTS.md", "CLAUDE.md", ".claude/rules/doctrine-migrations.md",
                    ".claude/rules/doctrine-tests.md", ".doctrine/graph.json", ".doctrine/.gitignore"):
            self.assertTrue((root / rel).is_file(), rel)
        self.assertIn("@AGENTS.md", (root / "CLAUDE.md").read_text())
        graph = json.loads((root / ".doctrine" / "graph.json").read_text())
        self.assertEqual(graph["schema"], "doctrine-map/graph@1")
        self.assertFalse((root / ".rulesync").exists(), "rulesync is written only on request")

    def test_build_twice_changes_nothing(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=REFERENCE.read_text(encoding="utf-8"))
        self.build(root)
        before = snapshot(root)
        out = self.build(root)
        self.assertIn("0 written", out)
        self.assertEqual(snapshot(root), before)

    def test_user_text_outside_the_region_survives(self):
        mine = "# Agents\n\nRun `make test` before you push.\n"
        root = self.make_repo(dict(DEMO_FILES, **{"AGENTS.md": mine, "CLAUDE.md": "Use British English.\n"}))
        self.build(root)
        agents = (root / "AGENTS.md").read_text()
        self.assertTrue(agents.startswith(mine))
        self.assertTrue((root / "CLAUDE.md").read_text().startswith("Use British English.\n"))
        edited = agents.replace(mine, "# Agents, renamed\n")
        (root / "AGENTS.md").write_text(edited)
        self.build(root)
        self.assertEqual((root / "AGENTS.md").read_text(), edited)

    def test_a_removed_route_takes_its_rule_file_with_it(self):
        root = self.make_repo(DEMO_FILES)
        hand_written = root / ".claude" / "rules" / "doctrine-notes.md"
        hand_written.parent.mkdir(parents=True)
        hand_written.write_text("My own rule, not generated.\n")
        self.build(root)
        smaller = re.sub(r'\[\[route\]\]\nid = "tests".*', "", MINI, flags=re.S)
        (root / ".doctrine" / "doctrine.toml").write_text(smaller)
        out = self.build(root)
        self.assertIn("doctrine-tests.md (removed)", out)
        self.assertFalse((root / ".claude" / "rules" / "doctrine-tests.md").exists())
        self.assertTrue(hand_written.exists(), "files without the generated header are never removed")

    def test_rulesync_export_stays_in_step_once_made(self):
        root = self.make_repo(DEMO_FILES)
        self.build(root, "--export", "rulesync")
        rule = root / ".rulesync" / "rules" / "doctrine-migrations.md"
        self.assertTrue(rule.is_file())
        (root / ".doctrine" / "doctrine.toml").write_text(MINI.replace("change database structure", "change the schema"))
        self.build(root)
        self.assertIn("change the schema", rule.read_text())

    def test_broken_markers_stop_the_build(self):
        root = self.make_repo(dict(DEMO_FILES, **{"AGENTS.md": f"{doctrine.BEGIN}\nhalf a region\n"}))
        code, out, err = self.run_cli(root, "build")
        self.assertEqual(code, 2)
        self.assertIn("unbalanced", err)
        self.assertEqual((root / "AGENTS.md").read_text(), f"{doctrine.BEGIN}\nhalf a region\n")


class Walk(RepoTestCase):
    def test_git_walk_lists_tracked_and_untracked_but_not_ignored(self):
        root = self.make_repo(dict(DEMO_FILES, **{".gitignore": "secret.log\n", "secret.log": "x"}), git=True)
        files = doctrine.repo_files(root)
        self.assertIn("src/server.js", files)
        self.assertNotIn("secret.log", files)

    def test_plain_walk_skips_dependency_folders_and_local_state(self):
        root = self.make_repo(dict(DEMO_FILES, **{"node_modules/x/index.js": "", ".doctrine/sessions/a.json": "",
                                                  ".doctrine/graph.json": "{}"}))
        files = doctrine.repo_files(root)
        self.assertIn("db/migrations/001_init.sql", files)
        self.assertIn(".doctrine/doctrine.toml", files)
        self.assertFalse(any(f.startswith(("node_modules/", ".doctrine/sessions/")) for f in files))
        self.assertNotIn(".doctrine/graph.json", files)


if __name__ == "__main__":
    unittest.main()
