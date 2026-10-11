"""The doctrine model: loading, validation, routing and glob semantics."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from doctrine_testkit import MINI, REFERENCE, RepoTestCase, doctrine


class ReferenceDoctrine(unittest.TestCase):
    def test_reference_doctrine_loads(self):
        d = doctrine.load(REFERENCE)
        self.assertEqual((len(d.axioms), len(d.principles), len(d.routes), len(d.sources)), (7, 15, 9, 19))
        self.assertEqual(d.name, "safety-core")
        self.assertTrue(all(p.anti for p in d.principles.values()), "every principle has an anti-principle")

    def test_entry_card_fits_its_budget(self):
        d = doctrine.load(REFERENCE)
        lines = d.entry_lines()
        self.assertLessEqual(len(lines), d.entry_budget_lines)
        self.assertEqual(sum(1 for line in lines if line.startswith("- P")), 15)
        self.assertIn("python3 doctrine.py explain", lines[-1])


class Globs(unittest.TestCase):
    CASES = [
        ("docs/**", "docs/a/b.md", True),
        ("docs/**", "docs", True),
        ("docs/**", "src/docs/a.md", False),
        ("**/migrations/**", "db/migrations/001.sql", True),
        ("**/migrations/**", "migrations/001.sql", True),
        ("**/*.sql", "a/b/c.sql", True),
        ("**/*.sql", "c.sql", True),
        ("*.md", "deep/down/x.md", True),
        ("README*", "pkg/README.md", True),
        ("package.json", "apps/web/package.json", True),
        ("Dockerfile", "Dockerfile", True),
        ("src/app", "src/app/main.py", True),
        ("src/app", "src/application.py", False),
        (".env", ".env", True),
        (".env.*", "config/.env.local", True),
        (".env.*", ".envrc", False),
        ("scripts/release*", "scripts/release.sh", True),
        ("scripts/release*", "other/scripts/release.sh", False),
        ("tests/?.py", "tests/a.py", True),
        ("tests/?.py", "tests/ab.py", False),
        ("tests/*", "tests/sub/a.py", True),
    ]

    def test_glob_semantics(self):
        for pattern, path, expected in self.CASES:
            with self.subTest(pattern=pattern, path=path):
                self.assertEqual(doctrine.glob_match(pattern, path), expected)

    def test_paths_are_normalised(self):
        self.assertEqual(doctrine.normalise("./a\\b/"), "a/b")
        self.assertTrue(doctrine.glob_match("db/**", "./db/x.sql"))


class Validation(unittest.TestCase):
    def raw(self) -> dict:
        return tomllib.loads(MINI)

    def problems(self, raw: dict) -> list[str]:
        with self.assertRaises(doctrine.DoctrineError) as caught:
            doctrine.from_dict(raw)
        return caught.exception.problems

    def test_every_problem_is_reported_at_once(self):
        raw = self.raw()
        raw["principle"].append(dict(raw["principle"][0]))  # duplicate P1
        raw["principle"][1]["axioms"] = ["A9"]
        raw["principle"][2]["anti"] = ""
        raw["principle"][2]["enforcement"] = "maybe"
        raw["axiom"][0]["sources"] = [{"ref": "nowhere"}]
        raw["route"][0]["principles"] = ["P9"]
        raw["route"][0]["on"] = ["deploy"]
        raw["route"][1]["id"] = "../escape"
        problems = self.problems(raw)
        for expected in ("duplicate principle id P1", "serves unknown axiom A9", "P3 has no anti-principle",
                         "enforcement must be one of", "cites unknown source nowhere",
                         "names unknown principle P9", "trigger 'deploy'", "id may hold only"):
            self.assertTrue(any(expected in p for p in problems), (expected, problems))

    def test_at_most_seven_axioms(self):
        raw = self.raw()
        raw["axiom"] = [dict(raw["axiom"][0], id=f"A{i}") for i in range(1, 9)]
        self.assertTrue(any("at most seven" in p for p in self.problems(raw)))

    def test_route_and_source_need_their_fields(self):
        raw = self.raw()
        raw["route"][0]["paths"] = []
        raw["source"][0]["url"] = ""
        problems = self.problems(raw)
        self.assertIn("route migrations has no paths", problems)
        self.assertIn("source s1 has no url", problems)


class Queries(RepoTestCase):
    def test_routes_and_principles_for_a_path(self):
        d = doctrine.from_dict(tomllib.loads(MINI))
        self.assertEqual([r.id for r in d.routes_for("db/migrations/001.sql")], ["migrations"])
        self.assertEqual(d.routes_for("db/x.sql", trigger="read"), [])
        self.assertEqual([p.id for p in d.principles_for("db/x.sql", trigger="shell")], ["P1"])
        self.assertEqual([p.id for p in d.global_principles()], ["P3"])

    def test_find_doctrine_walks_up_to_either_layout(self):
        root = self.make_repo({"src/deep/x.py": ""})
        found = doctrine.find_doctrine(root / "src" / "deep")
        self.assertEqual(found, root / ".doctrine" / "doctrine.toml")
        self.assertEqual(doctrine.repo_root(found), root)
        flat = self.make_repo({"a.txt": ""}, layout="flat")
        self.assertEqual(doctrine.repo_root(doctrine.find_doctrine(flat)), flat)

    def test_entry_card_names_the_script_for_each_layout(self):
        dotted = doctrine.load(self.make_repo() / ".doctrine" / "doctrine.toml")
        self.assertIn("python3 .doctrine/doctrine.py explain", dotted.entry_lines()[-1])
        flat = doctrine.load(self.make_repo(layout="flat") / "doctrine.toml")
        self.assertIn("python3 doctrine.py explain", flat.entry_lines()[-1])

    def test_relative_to_root(self):
        root = self.make_repo({"a/b.txt": ""})
        self.assertEqual(doctrine.relative_to_root(root / "a" / "b.txt", root), "a/b.txt")
        self.assertIsNone(doctrine.relative_to_root(Path("/"), root))


if __name__ == "__main__":
    unittest.main()
