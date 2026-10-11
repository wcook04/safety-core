"""Projections: managed regions, rule file formats and glob export."""

from __future__ import annotations

import json
import re
import unittest

from doctrine_testkit import DEMO_FILES, REFERENCE, RepoTestCase, doctrine


def strict_glob(pattern: str, path: str) -> bool:
    """A plain glob matcher with no extras, as other tools read globs: `**/` spans zero or
    more folders, `*` and `?` stay inside one segment, nothing matches beneath a match."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("/**", i) and i + 3 == len(pattern):
            out.append("/.*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.fullmatch("".join(out), path) is not None


class ExportGlobs(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(doctrine.export_globs(["docs/**"]), ["docs/**", "docs"])
        self.assertEqual(doctrine.export_globs(["README*"]), ["**/README*", "**/README*/**"])
        self.assertEqual(doctrine.export_globs(["src/app"]), ["src/app", "src/app/**"])
        self.assertEqual(doctrine.export_globs(["**/migrations/**", "db/**"]),
                         ["**/migrations/**", "**/migrations", "db/**", "db"])

    def test_exported_globs_mean_what_the_route_means(self):
        paths = ["README.md", "pkg/README.md", "docs", "docs/a.md", "src/app/x.py", "src/app",
                 "src/application.py", "db/m/001.sql", "x.sql", ".env", "a/.env.local", ".envrc",
                 "Dockerfile", "svc/Dockerfile", "Dockerfile/inner", "scripts/release.sh", "release/notes.md",
                 "tests/a.test.js", "lib/a_test.go", ".github/workflows/ci.yml", "deep/.github/workflows/ci.yml"]
        for route in doctrine.load(REFERENCE).routes.values():
            globs = doctrine.export_globs(route.paths)
            for path in paths:
                with self.subTest(route=route.id, path=path):
                    self.assertEqual(route.matches(path), any(strict_glob(g, path) for g in globs))


class Regions(unittest.TestCase):
    def test_splice_creates_replaces_and_keeps_the_rest(self):
        made = doctrine.splice(None, "card\n")
        self.assertEqual(made, f"{doctrine.BEGIN}\ncard\n{doctrine.END}\n")
        mine = "# My notes\n\nKeep this.\n"
        added = doctrine.splice(mine, "card\n")
        self.assertTrue(added.startswith(mine))
        self.assertEqual(doctrine.region_of(added), "card\n")
        replaced = doctrine.splice(added + "\nAfter.\n", "new card\n")
        self.assertTrue(replaced.startswith(mine) and replaced.endswith("\nAfter.\n"))
        self.assertEqual(doctrine.region_of(replaced), "new card\n")
        self.assertEqual(doctrine.splice(replaced, "new card\n"), replaced)

    def test_crlf_files_keep_their_line_endings(self):
        text = "line one\r\nline two\r\n"
        spliced = doctrine.splice(text, "card\nmore\n")
        self.assertNotIn("\n", spliced.replace("\r\n", ""))
        self.assertEqual(doctrine.region_of(spliced), "card\nmore\n")

    def test_unbalanced_markers_are_refused(self):
        with self.assertRaises(ValueError):
            doctrine.region_of(f"{doctrine.BEGIN}\nno end\n")
        with self.assertRaises(ValueError):
            doctrine.splice(f"{doctrine.END}\n{doctrine.BEGIN}\n", "card\n")


class Formats(RepoTestCase):
    def setUp(self):
        self.root = self.make_repo(DEMO_FILES, doctrine_text=REFERENCE.read_text(encoding="utf-8"))
        self.repo = doctrine.open_repo(self.root / ".doctrine" / "doctrine.toml")
        self.outs = doctrine.outputs(self.repo, rulesync=True)

    def test_agents_md_holds_the_entry_card_and_where_rules_live(self):
        kind, text = self.outs["AGENTS.md"]
        self.assertEqual(kind, "region")
        lines = text.splitlines()
        self.assertIn(doctrine.GENERATED, lines[0])
        self.assertIn(".doctrine/doctrine.toml", lines[0])
        for line in self.repo.doctrine.entry_lines():
            self.assertIn(line, lines)
        self.assertIn("| Route | Paths | Principles |", lines)
        self.assertTrue(any(line.startswith("| migrations | `**/migrations/**`") for line in lines))

    def test_claude_md_imports_agents_md(self):
        kind, text = self.outs["CLAUDE.md"]
        lines = text.splitlines()
        self.assertEqual((kind, len(lines)), ("region", 3))
        self.assertEqual(lines[1], "@AGENTS.md")
        self.assertIn(".claude/rules/doctrine-*.md", lines[2])

    def test_claude_rule_has_paths_front_matter_then_the_header(self):
        kind, text = self.outs[".claude/rules/doctrine-migrations.md"]
        lines = text.splitlines()
        self.assertEqual((kind, lines[0], lines[1]), ("file", "---", "paths:"))
        end = lines.index("---", 1)
        globs = [json.loads(line.removeprefix("  - ")) for line in lines[2:end]]
        self.assertEqual(globs, doctrine.export_globs(self.repo.doctrine.routes["migrations"].paths))
        self.assertIn(doctrine.GENERATED, lines[end + 1])
        body = "\n".join(lines)
        for pid in ("P2", "P4"):
            p = self.repo.doctrine.principles[pid]
            self.assertIn(p.one, body)
            self.assertIn(p.three, body)
        self.assertIn(self.repo.doctrine.routes["migrations"].reminder, body)

    def test_rulesync_rule_follows_its_file_format(self):
        kind, text = self.outs[".rulesync/rules/doctrine-tests.md"]
        lines = text.splitlines()
        end = lines.index("---", 1)
        front = dict(line.split(": ", 1) for line in lines[1:end])
        self.assertEqual(front["root"], "false")
        self.assertEqual(json.loads(front["targets"]), ["*"])
        self.assertEqual(json.loads(front["globs"]), doctrine.export_globs(self.repo.doctrine.routes["tests"].paths))
        self.assertEqual(json.loads(front["description"]), self.repo.doctrine.routes["tests"].reminder)


if __name__ == "__main__":
    unittest.main()
