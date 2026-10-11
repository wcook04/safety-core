"""Shared fixtures for the hooks tests: temporary git repositories and synthetic secrets.

Synthetic keys are built by concatenation so no source file holds a key-shaped string.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import hooks  # noqa: E402

HOOKS_PY = ROOT / "hooks.py"
GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.org",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.org",
    "PYTHONDONTWRITEBYTECODE": "1",
}


def fake_aws_key() -> str:
    return "AK" + "IA" + "QWERTYUI" + "OPASDFGH"


def fake_github_token() -> str:
    return "gh" + "p_" + "a1B2c3D4e5" * 4


def fake_private_key_header() -> str:
    return "-----BEGIN " + "OPENSSH PRIVATE" + " KEY-----"


def run_git(cwd, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout


class HookCase(unittest.TestCase):
    """A temporary repository with the reference doctrine, and helpers to call the hooks in-process."""

    remote = False
    hooks_table = ""
    doctrine = True

    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ, GIT_ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(os.path.realpath(tmp.name))
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.session = "test-" + uuid.uuid4().hex[:8]
        run_git(self.repo, "init", "-q", "-b", "main")
        if self.doctrine:
            text = (ROOT / "doctrine.toml").read_text(encoding="utf-8")
            if self.hooks_table:
                text += "\n[hooks]\n" + self.hooks_table + "\n"
            (self.repo / "doctrine.toml").write_text(text, encoding="utf-8")
        for rel, body in {
            "src/app.py": "def add(a, b):\n    return a + b\n",
            "tests/test_app.py": "from src.app import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
            "CLAUDE.md": "# Rules\n",
            "db/migrations/001.sql": "create table t (id int);\n",
            ".gitignore": "local/\n",
        }.items():
            self.write(rel, body)
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "-m", "initial")
        if self.remote:
            self.origin = self.base / "origin.git"
            run_git(self.base, "init", "-q", "--bare", str(self.origin))
            run_git(self.repo, "remote", "add", "origin", str(self.origin))
            run_git(self.repo, "push", "-q", "-u", "origin", "main")

    # -- helpers
    def write(self, rel: str, body: str) -> Path:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def git(self, *args: str) -> str:
        return run_git(self.repo, *args)

    def payload(self, event: str, **fields) -> dict:
        return dict({"session_id": self.session, "cwd": str(self.repo), "hook_event_name": event,
                     "transcript_path": "", "permission_mode": "default"}, **fields)

    def pre(self, tool: str, **tool_input):
        return hooks.handle(self.payload("PreToolUse", tool_name=tool, tool_input=tool_input))

    def bash(self, command: str):
        return self.pre("Bash", command=command)

    def post(self, tool: str, response=None, **tool_input):
        return hooks.handle(self.payload("PostToolUse", tool_name=tool, tool_input=tool_input, tool_response=response or {}))

    def ran(self, command: str, code: int = 0, **extra):
        """Record a Bash command the way Claude Code reports it: PostToolUse on success, PostToolUseFailure otherwise."""
        if code == 0:
            return self.post("Bash", {"stdout": "", "stderr": "", "interrupted": False, "isImage": False}, command=command, **extra)
        return hooks.handle(self.payload("PostToolUseFailure", tool_name="Bash", tool_input=dict(command=command, **extra),
                                         error=f"Exit code {code}\nsome output", is_interrupt=False))

    def edited(self, rel: str, body: str = "changed\n") -> None:
        """Change a file and record it as edited through the Edit tool."""
        self.write(rel, body)
        self.post("Edit", file_path=str(self.repo / rel), old_string="x", new_string="y")

    def stop(self, message: str, **fields):
        fields.setdefault("stop_hook_active", False)
        return hooks.handle(self.payload("Stop", last_assistant_message=message, **fields))

    def decision(self, out) -> str:
        return ((out or {}).get("hookSpecificOutput") or {}).get("permissionDecision", "")

    def reason(self, out) -> str:
        return ((out or {}).get("hookSpecificOutput") or {}).get("permissionDecisionReason", "")

    def context(self, out) -> str:
        return ((out or {}).get("hookSpecificOutput") or {}).get("additionalContext", "")

    def script(self, payload, *argv: str, raw: str | None = None):
        """Run hooks.py as Claude Code does: JSON on stdin. Returns (exit code, parsed stdout or None, stderr)."""
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        done = subprocess.run([sys.executable, str(HOOKS_PY), *argv], input=raw if raw is not None else json.dumps(payload),
                              capture_output=True, text=True, env=env, cwd=str(self.base))
        return done.returncode, (json.loads(done.stdout) if done.stdout.strip() else None), done.stderr


class SupportSelfTest(unittest.TestCase):
    def test_synthetic_keys_have_the_shapes_the_scanner_knows(self):
        self.assertEqual(hooks.shapes(fake_aws_key()), ["an AWS access key"])
        self.assertEqual(hooks.shapes(fake_github_token()), ["a GitHub token"])
        self.assertEqual(hooks.shapes(fake_private_key_header()), ["a private key block"])

    def test_no_source_file_holds_a_key_shape(self):
        sources = [HOOKS_PY, *sorted((ROOT / "tests").glob("test_hooks_*.py")), ROOT / "examples" / "demo.sh",
                   ROOT / "docs" / "HOOKS.md"]
        for path in sources:
            if path.exists():
                self.assertEqual(hooks.shapes(path.read_text(encoding="utf-8")), [], path.name)

    def test_git_is_available(self):
        self.assertIsNotNone(shutil.which("git"))


if __name__ == "__main__":
    unittest.main()
