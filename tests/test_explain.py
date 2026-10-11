"""explain: exactly what an agent receives at a path."""

from __future__ import annotations

import unittest

from doctrine_testkit import DEMO_FILES, REFERENCE, RepoTestCase, doctrine


class Explain(RepoTestCase):
    def setUp(self):
        self.root = self.make_repo(DEMO_FILES, doctrine_text=REFERENCE.read_text(encoding="utf-8"))
        self.d = doctrine.load(self.root / ".doctrine" / "doctrine.toml")

    def test_a_migration_path(self):
        code, out, _ = self.run_cli(self.root, "explain", "db/migrations/001_init.sql")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("db/migrations/001_init.sql\n"))
        for line in self.d.entry_lines():
            if line:
                self.assertIn(line, out)
        self.assertIn("migrations: rule file .claude/rules/doctrine-migrations.md; hook reminder on edit, shell", out)
        self.assertIn("Files here change database structure.", out)
        for pid in ("P2", "P4"):
            p = self.d.principles[pid]
            self.assertIn(f"{pid} {p.name}:", out)
            self.assertIn(p.one.split()[0], out)
        self.assertIn("P2 Ask before irreversible or publishing actions: enforced (ask; hook:pre_tool#irreversible", out)
        self.assertIn("P4 Keep the work recoverable: reminded (remind, declared advise; stop:claims#dirty_tree", out)
        self.assertIn("Enforced by hooks and checks: P1 ask, P6 block, P11 block, P14 check, P15 ask.", out)
        self.assertIn("Reminded or advised by hooks: P3 advise, P5 remind, P9 advise, P12 remind.", out)
        self.assertIn("Words only (the entry card): P7, P8, P10, P13.", out)

    def test_paths_resolve_from_the_current_folder(self):
        code, out, _ = self.run_cli(self.root, "explain", "migrations/001_init.sql", cwd=self.root / "db")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("db/migrations/001_init.sql\n"))

    def test_a_path_no_route_reaches(self):
        code, out, _ = self.run_cli(self.root, "explain", "src/server.js")
        self.assertEqual(code, 0)
        self.assertIn("No route matches this path", out)

    def test_a_path_outside_the_repository_is_refused(self):
        code, _, err = self.run_cli(self.root, "explain", "/")
        self.assertEqual(code, 2)
        self.assertIn("outside the repository", err)


if __name__ == "__main__":
    unittest.main()
