"""check: fails on missing enforcers, drift and an over-budget card; reports coverage honestly."""

from __future__ import annotations

import json
import unittest

from doctrine_testkit import DEMO_FILES, MINI, RepoTestCase


class Check(RepoTestCase):
    def test_passes_after_a_build_and_reports_coverage(self):
        root = self.make_repo(DEMO_FILES)
        self.build(root)
        code, out, _ = self.run_cli(root, "check")
        self.assertEqual(code, 0, out)
        self.assertIn("1 of 3 principles enforced beyond words", out)
        self.assertIn("Coverage by place", out)
        self.assertIn("check passed", out)
        self.assertIn("Task completeness, undeclared requirements and live hook execution are not evaluated", out)

    def test_valid_configuration_does_not_certify_an_incomplete_task(self):
        # A prohibitions/configuration pass cannot establish that a response
        # addressed every issue. Keep that boundary in the machine receipt.
        files = dict(DEMO_FILES, **{
            "work/request.txt": "A review reports a late appointment and a charge of 149 after a quote of 99.\n",
            "work/response.txt": "We are sorry your appointment started late.\n",
        })
        root = self.make_repo(files)
        self.build(root)
        code, out, _ = self.run_cli(root, "check", "--json")
        report = json.loads(out)
        self.assertEqual(code, 0, out)
        self.assertTrue(report["ok"])
        self.assertEqual(report["coverage"]["basis"], "declared_repository_configuration")
        self.assertIn("task_completeness", report["coverage"]["not_evaluated"])
        self.assertIn("undeclared_requirements", report["coverage"]["not_evaluated"])
        self.assertIn("live_hook_execution", report["coverage"]["not_evaluated"])

    def test_coverage_table_marks_each_place(self):
        root = self.make_repo(DEMO_FILES)
        self.build(root)
        code, out, _ = self.run_cli(root, "check", "--json")
        report = json.loads(out)
        self.assertTrue(report["ok"])
        places = report["places"]
        self.assertEqual(places["db"], {"P1": "enforced", "P2": "words", "P3": "words"})
        self.assertEqual(places["tests"], {"P1": "enforced", "P2": "reminded", "P3": "words"})
        self.assertEqual(report["principles"]["P2"]["effective"], "remind")

    def test_a_hand_edited_region_fails_the_check(self):
        root = self.make_repo(DEMO_FILES)
        self.build(root)
        agents = root / "AGENTS.md"
        agents.write_text(agents.read_text().replace("Irreversible actions wait for a person.", "Do what you like."))
        code, out, _ = self.run_cli(root, "check")
        self.assertEqual(code, 1)
        self.assertIn("stale_projection", out)
        self.assertIn("AGENTS.md", out)
        self.build(root)
        self.assertEqual(self.run_cli(root, "check")[0], 0)

    def test_a_missing_enforcer_fails_the_check(self):
        root = self.make_repo(DEMO_FILES, hooks="CHECKS = {}\n")
        self.build(root)
        code, out, _ = self.run_cli(root, "check")
        self.assertEqual(code, 1)
        self.assertIn("P1 names hook:pre_tool#irreversible, which is missing", out)

    def test_a_declared_level_with_nothing_behind_it_fails(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=MINI.replace('enforcement = "prose"', 'enforcement = "block"'))
        self.build(root)
        code, out, _ = self.run_cli(root, "check")
        self.assertEqual(code, 1)
        self.assertIn("P3 declares block but names no enforcer", out)

    def test_an_over_budget_entry_card_fails(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=MINI.replace("entry_budget_lines = 40", "entry_budget_lines = 4"))
        self.build(root)
        code, out, _ = self.run_cli(root, "check")
        self.assertEqual(code, 1)
        self.assertIn("over_budget", out)

    def test_dead_routes_and_unrouted_sensitive_places_only_warn(self):
        files = dict(DEMO_FILES, **{"infra/main.tf": "", ".github/workflows/ci.yml": ""})
        files.pop("tests/orders.test.js")
        quiet = MINI.replace('enforcement = "remind"\nenforced_by = ["route:tests"]', 'enforcement = "prose"')
        root = self.make_repo(files, doctrine_text=quiet)
        self.build(root)
        code, out, _ = self.run_cli(root, "check")
        self.assertEqual(code, 0, out)
        self.assertIn("dead_route", out)
        self.assertIn("unrouted_sensitive", out)
        self.assertIn(".github/workflows", out)
        self.assertIn("check passed, ", out)

    def test_unwired_hooks_are_reported(self):
        root = self.make_repo(DEMO_FILES, wired=False)
        self.build(root)
        _, out, _ = self.run_cli(root, "check")
        self.assertIn("hooks_unwired", out)
        (root / ".claude" / "settings.json").write_text(json.dumps(
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR"/.doctrine/hooks.py'}]}]}}))
        _, out, _ = self.run_cli(root, "check")
        self.assertNotIn("hooks_unwired", out)

    def test_a_malformed_doctrine_is_reported_not_raised(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=MINI.replace('anti = "Acting blindly."', ""))
        code, _, err = self.run_cli(root, "check")
        self.assertEqual(code, 2)
        self.assertIn("axiom A1 has no anti-axiom", err)


if __name__ == "__main__":
    unittest.main()
