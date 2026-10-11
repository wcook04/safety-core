"""The graph (doctrine-map/graph@1): shape, stable ids, places, gaps and effective levels."""

from __future__ import annotations

import json
import unittest

from doctrine_testkit import DEMO_FILES, MINI, REFERENCE, RepoTestCase, doctrine


class Graph(RepoTestCase):
    def graph(self, root):
        graph, notes = doctrine.build_graph(doctrine.open_repo(self.doctrine_path(root)))
        return graph, notes, {n["id"]: n for n in graph["nodes"]}

    def test_schema_shape(self):
        graph, _, nodes = self.graph(self.make_repo(DEMO_FILES))
        self.assertEqual(set(graph), {"schema", "generated_at", "repository", "doctrine", "entry", "nodes",
                                      "edges", "gaps", "coverage"})
        self.assertRegex(graph["generated_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(graph["doctrine"]["source"], ".doctrine/doctrine.toml")
        self.assertEqual(len(graph["doctrine"]["sha256"]), 64)
        self.assertEqual(graph["entry"]["used"], len(graph["entry"]["lines"]))
        self.assertEqual({n["kind"] for n in nodes.values()}, {"axiom", "principle", "route", "place", "enforcer", "source"})
        self.assertEqual({e["kind"] for e in graph["edges"]}, {"serves", "applies", "governs", "enforced_by", "cites"})
        for edge in graph["edges"]:
            self.assertIn(edge["from"], nodes)
            self.assertIn(edge["to"], nodes)
        self.assertEqual(set(nodes["P1"]) - {"id", "kind", "name"},
                         {"one", "three", "anti", "axioms", "declared", "effective", "enforcers", "global", "sources"})
        self.assertEqual(nodes["enf:hook:pre_tool#irreversible"]["file"], ".doctrine/hooks.py")
        json.dumps(graph)

    def test_ids_are_stable_across_rebuilds(self):
        root = self.make_repo(DEMO_FILES, doctrine_text=REFERENCE.read_text(encoding="utf-8"))
        first, _, _ = self.graph(root)
        second, _, _ = self.graph(root)
        self.assertEqual([n["id"] for n in first["nodes"]], [n["id"] for n in second["nodes"]])
        self.assertEqual(first["edges"], second["edges"])

    def test_places_are_folders_at_depth_one_and_two_plus_routed_root_files(self):
        _, _, nodes = self.graph(self.make_repo(dict(DEMO_FILES, **{"db/migrations/deep/x.sql": ""})))
        places = {n["path"]: n for n in nodes.values() if n["kind"] == "place"}
        self.assertIn("db", places)
        self.assertIn("db/migrations", places)
        self.assertNotIn("db/migrations/deep", places)
        self.assertNotIn("README.md", places, "the mini doctrine routes no root file")
        self.assertEqual(places["db"]["files"], 2)
        self.assertEqual(places["db"]["name"], "db/")
        self.assertEqual(places["db/migrations"]["routes"], ["route:migrations"])
        self.assertEqual(places["db/migrations"]["principles"], ["P1"])
        self.assertTrue(places["db"]["sensitive"])

    def test_effective_level_comes_from_what_exists(self):
        _, _, nodes = self.graph(self.make_repo(DEMO_FILES))
        self.assertEqual((nodes["P1"]["declared"], nodes["P1"]["effective"]), ("ask", "ask"))
        self.assertEqual(nodes["P2"]["effective"], "remind")
        self.assertEqual(nodes["P3"]["effective"], "prose")
        self.assertTrue(nodes["P3"]["global"])

        missing_hook = self.make_repo(DEMO_FILES, hooks="CHECKS = {}\n")
        graph, _, nodes = self.graph(missing_hook)
        self.assertEqual(nodes["P1"]["effective"], "remind", "the migrations route still reminds")
        self.assertEqual(nodes["P1"]["enforcers"], [{"ref": "hook:pre_tool#irreversible", "status": "missing", "level": None}])
        self.assertIn({"kind": "missing_enforcer", "id": "P1"}, [{k: g[k] for k in ("kind", "id")} for g in graph["gaps"]])

    def test_gaps(self):
        files = dict(DEMO_FILES, **{"infra/main.tf": "", ".env.production": ""})
        files.pop("tests/orders.test.js")
        graph, _, _ = self.graph(self.make_repo(files))
        kinds = {(g["kind"], g.get("id") or g.get("path")) for g in graph["gaps"]}
        self.assertIn(("dead_route", "route:tests"), kinds)
        self.assertIn(("prose_only", "P3"), kinds)
        self.assertIn(("missing_enforcer", "P2"), kinds, "route:tests matches nothing")
        self.assertIn(("unrouted_sensitive", "place:infra"), kinds)
        self.assertIn(("unrouted_sensitive", "place:.env.production"), kinds)
        self.assertEqual(graph["coverage"]["routes_dead"], 1)

    def test_over_budget_entry_card(self):
        graph, _, _ = self.graph(self.make_repo(DEMO_FILES, doctrine_text=MINI.replace("entry_budget_lines = 40", "entry_budget_lines = 5")))
        self.assertIn("over_budget", [g["kind"] for g in graph["gaps"]])

    def test_coverage_counts(self):
        graph, _, _ = self.graph(self.make_repo(DEMO_FILES))
        cov = graph["coverage"]
        self.assertEqual(cov["by_level"], {"block": 0, "ask": 1, "check": 0, "remind": 1, "advise": 0, "prose": 1})
        self.assertEqual((cov["principles"], cov["enforced_beyond_words"]), (3, 2))
        self.assertEqual(cov["files_governed"], 2)
        self.assertEqual(cov["files_total"], len(DEMO_FILES) + 2)  # plus .doctrine/doctrine.toml and hooks.py


class Guards(RepoTestCase):
    def settings(self, *commands):
        hooks = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": c} for c in commands]}]}
        return {".claude/settings.json": json.dumps({"hooks": hooks})}

    def graph(self, files, doctrine_text=MINI):
        repo = doctrine.open_repo(self.make_repo(dict(DEMO_FILES, **files), doctrine_text=doctrine_text,
                                                 hooks="CHECKS = {}\n") / ".doctrine" / "doctrine.toml")
        graph, _ = doctrine.build_graph(repo)
        return graph, {n["id"]: n for n in graph["nodes"]}

    def test_a_wired_guard_is_credited_for_the_checks_it_stands_in_for(self):
        graph, nodes = self.graph(self.settings("/usr/local/bin/dcg"))
        self.assertIn({"ref": "guard:dcg", "status": "present", "level": "ask", "by": "dcg"}, nodes["P1"]["enforcers"])
        self.assertEqual(nodes["P1"]["effective"], "ask")
        self.assertEqual(nodes["enf:guard:dcg"]["type"], "guard")

    def test_secrets_credit_follows_each_tool(self):
        reference = REFERENCE.read_text(encoding="utf-8")
        _, nodes = self.graph(self.settings("npx -y cc-safety-net@latest hook"), reference)
        self.assertIn("guard:cc-safety-net", [e["ref"] for e in nodes["P11"]["enforcers"]])
        self.assertEqual(nodes["P11"]["effective"], "block")
        _, nodes = self.graph(self.settings("dcg"), reference)
        self.assertNotIn("guard:dcg", [e["ref"] for e in nodes["P11"]["enforcers"]], "dcg scans no secrets by default")

    def test_cupcake_counts_only_where_a_principle_names_it(self):
        _, nodes = self.graph(self.settings("cupcake eval --harness claude"))
        self.assertEqual([e["ref"] for e in nodes["P1"]["enforcers"]], ["hook:pre_tool#irreversible"])
        named = MINI.replace('enforced_by = ["hook:pre_tool#irreversible"]', 'enforced_by = ["guard:cupcake"]')
        _, nodes = self.graph(self.settings("cupcake eval --harness claude"), named)
        self.assertEqual(nodes["P1"]["enforcers"], [{"ref": "guard:cupcake", "status": "present", "level": "ask", "by": "cupcake"}])
        _, nodes = self.graph({}, named)
        self.assertEqual(nodes["P1"]["enforcers"][0]["status"], "missing")

    def test_unwired_commands_earn_nothing(self):
        _, nodes = self.graph(self.settings("echo hello"))
        self.assertEqual(len(nodes["P1"]["enforcers"]), 1)


if __name__ == "__main__":
    unittest.main()
