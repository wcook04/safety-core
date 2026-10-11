"""Shared fixtures for the doctrine.py tests: temporary repositories and a captured CLI run."""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import doctrine  # noqa: E402

REFERENCE = ROOT / "doctrine.toml"

MINI = """\
[doctrine]
name = "mini"
version = "1.0"
summary = "A small doctrine for tests."
entry_budget_lines = 40

[[source]]
id = "s1"
title = "Source one"
url = "https://example.org/one"

[[axiom]]
id = "A1"
name = "Ask first"
clause = "irreversible(a) => ask(a)"
plain = "Irreversible actions wait for a person."
anti = "Acting blindly."
sources = [{ ref = "s1", quote = "ask first" }]

[[principle]]
id = "P1"
axioms = ["A1"]
name = "Ask before irreversible actions"
one = "Irreversible actions wait for a person."
three = "Force pushes and migrations cannot be undone cheaply, so the agent asks first."
anti = "Deleting because the command was available."
enforcement = "ask"
enforced_by = ["hook:pre_tool#irreversible"]
sources = [{ ref = "s1" }]

[[principle]]
id = "P2"
axioms = ["A1"]
name = "Fix the code, not the test"
one = "Never weaken tests to get a pass."
three = "Tests decide whether the code works."
anti = "Gaming the grader."
enforcement = "remind"
enforced_by = ["route:tests"]

[[principle]]
id = "P3"
axioms = ["A1"]
name = "Say when you did less"
one = "Say what was skipped."
three = "A smaller result delivered silently reads as the full result."
anti = "A watered-down result presented as the whole."
enforcement = "prose"

[[route]]
id = "migrations"
paths = ["**/migrations/**", "db/**"]
principles = ["P1"]
reminder = "Files here change database structure."
on = ["edit", "shell"]

[[route]]
id = "tests"
paths = ["tests/**"]
principles = ["P2"]
reminder = "These files decide whether the code works."
"""

# A stand-in for hooks.py: only its literal CHECKS dict is ever read.
FAKE_HOOKS = '''"""Test stand-in for hooks.py."""
CHECKS = {
    "bypass_checks": {"principles": ["P1"], "level": "ask"},
    "irreversible": {"principles": ["P1", "P2"], "level": "ask"},
    "permission_gate": {"principles": ["P3"], "level": "advise"},
    "dirty_tree": {"principles": ["P4"], "level": "advise"},
    "masked_status": {"principles": ["P5"], "level": "remind"},
    "unsupported_claim": {"principles": ["P6"], "level": "block"},
    "unlogged_mistake": {"principles": ["P9"], "level": "advise"},
    "secrets": {"principles": ["P11"], "level": "block"},
    "untrusted_content": {"principles": ["P12"], "level": "remind"},
    "rule_files": {"principles": ["P15"], "level": "ask"},
}
raise SystemExit("never run me")
'''

DEMO_FILES = {
    "README.md": "# Orders\n",
    "package.json": '{"name": "orders"}\n',
    "src/server.js": "// server\n",
    "src/api/orders.js": "// orders\n",
    "tests/orders.test.js": "// test\n",
    "db/migrations/001_init.sql": "CREATE TABLE orders (id int);\n",
    "docs/guide.md": "# Guide\n",
}


class RepoTestCase(unittest.TestCase):
    """A test case that makes throwaway repositories and runs doctrine.py inside them."""

    def make_repo(self, files: dict[str, str] | None = None, doctrine_text: str = MINI,
                  layout: str = "dotdir", hooks: str | None = FAKE_HOOKS, git: bool = False) -> Path:
        root = Path(tempfile.mkdtemp(prefix="doctrine-test-")).resolve()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for rel, text in (files or {}).items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        if doctrine_text is not None:
            target = root / ".doctrine" / "doctrine.toml" if layout == "dotdir" else root / "doctrine.toml"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(doctrine_text, encoding="utf-8")
        if hooks is not None:
            (root / ".doctrine").mkdir(exist_ok=True)
            (root / ".doctrine" / "hooks.py").write_text(hooks, encoding="utf-8")
        if git:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        return root

    def doctrine_path(self, root: Path) -> Path:
        dotted = root / ".doctrine" / "doctrine.toml"
        return dotted if dotted.exists() else root / "doctrine.toml"

    def run_cli(self, root: Path, *argv: str, cwd: Path | None = None) -> tuple[int, str, str]:
        """Run doctrine.main with --doctrine pointing into `root`; returns (code, stdout, stderr)."""
        args = list(argv)
        if args and args[0] != "init" and "--doctrine" not in args:
            args += ["--doctrine", str(self.doctrine_path(root))]
        out, err = io.StringIO(), io.StringIO()
        previous = Path.cwd()
        os.chdir(cwd or root)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = doctrine.main(args)
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def build(self, root: Path, *extra: str) -> str:
        code, out, err = self.run_cli(root, "build", *extra)
        self.assertEqual(code, 0, out + err)
        return out
