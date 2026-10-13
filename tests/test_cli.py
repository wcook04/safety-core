"""The command line: log-error, map --out, errors and the script entry point."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest

from doctrine_testkit import DEMO_FILES, ROOT, RepoTestCase


class LogError(RepoTestCase):
    def test_appends_one_json_line_per_mistake(self):
        root = self.make_repo(DEMO_FILES)
        for n in (1, 2):
            code, out, _ = self.run_cli(root, "log-error", f"claimed tests passed ({n})", "--principle", "P1",
                                        "--lesson", "run the tests before saying they pass")
            self.assertEqual(code, 0)
        lines = (root / ".doctrine" / "mistakes.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 2)
        record = json.loads(lines[1])
        self.assertEqual((record["what"], record["principles"], record["lesson"]),
                         ("claimed tests passed (2)", ["P1"], "run the tests before saying they pass"))
        self.assertRegex(record["time"], r"^\d{4}-\d\d-\d\dT")
        self.assertIn("mistakes.jsonl", (root / ".doctrine" / ".gitignore").read_text())

    def test_unknown_principles_are_refused(self):
        root = self.make_repo(DEMO_FILES)
        code, _, err = self.run_cli(root, "log-error", "oops", "--principle", "P99", "--lesson", "x")
        self.assertEqual(code, 2)
        self.assertIn("unknown principle P99", err)
        self.assertFalse((root / ".doctrine" / "mistakes.jsonl").exists())


class MapOut(RepoTestCase):
    def test_writes_one_file_with_the_graph_inside(self):
        root = self.make_repo(DEMO_FILES)
        (root / ".doctrine" / "map.html").write_text(
            '<html><head></head><body><script id="doctrine-graph" type="application/json"></script>'
            "<script>/* viewer */</script></body></html>")
        out_file = root / "out" / "map.html"
        out_file.parent.mkdir()
        code, out, _ = self.run_cli(root, "map", "--out", str(out_file))
        self.assertEqual(code, 0, out)
        html = out_file.read_text()
        data = re.search(r'<script id="doctrine-graph" type="application/json">(.*?)</script>', html, re.S).group(1)
        self.assertNotIn("<", data)
        self.assertEqual(json.loads(data)["schema"], "doctrine-map/graph@1")
        self.assertIn("/* viewer */", html)

    def test_the_real_viewer_takes_the_graph(self):
        if not (ROOT / "map.html").is_file():
            self.skipTest("map.html is not in this checkout")
        root = self.make_repo(DEMO_FILES)
        out_file = root / "doctrine-map.html"
        code, out, _ = self.run_cli(root, "map", "--out", str(out_file))
        self.assertEqual(code, 0, out)
        html = out_file.read_text()
        self.assertEqual(html.count('id="doctrine-graph"'), 1)
        self.assertIn('"schema": "doctrine-map/graph@1"', html)


class Errors(RepoTestCase):
    def test_no_doctrine_here(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=None, hooks=None)
        code, _, err = self.run_cli(root, "check", "--doctrine", str(root / "doctrine.toml"))
        self.assertEqual(code, 2)
        self.assertIn("python3 doctrine.py init", err)

    def test_safety_entry_point_is_copied_and_runs_inside_the_target(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=None, hooks=None)
        setup = subprocess.run([sys.executable, str(ROOT / "safety.py"), "init", "--target", str(root)],
                               cwd=root, capture_output=True, text=True)
        self.assertEqual(setup.returncode, 0, setup.stderr)
        self.assertTrue((root / ".doctrine/safety.py").is_file())
        self.assertIn(".doctrine/safety.py check", setup.stdout)
        checked = subprocess.run([sys.executable, ".doctrine/safety.py", "check", "--json"],
                                 cwd=root, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertTrue(json.loads(checked.stdout)["ok"])

    def test_the_script_runs_as_a_program(self):
        done = subprocess.run([sys.executable, str(ROOT / "doctrine.py"), "--help"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)
        for command in ("init", "build", "check", "explain", "map", "log-error"):
            self.assertIn(command, done.stdout)


if __name__ == "__main__":
    unittest.main()
