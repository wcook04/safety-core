"""Each hook event end to end: what PreToolUse, PostToolUse, SessionStart return, and how modes change it."""

from __future__ import annotations

import ast
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_hooks_support import ROOT, HookCase, fake_aws_key, fake_github_token, hooks  # noqa: E402


class Reminders(HookCase):
    def test_edit_delivers_route_reminder_once_per_session(self):
        out = self.pre("Edit", file_path=str(self.repo / "tests/test_app.py"), old_string="a", new_string="b")
        text = self.context(out)
        self.assertIn('routes `tests/test_app.py` to "tests"', text)
        self.assertIn("P7 Fix the code, not the test", text)
        self.assertEqual(self.decision(out), "")
        self.assertIsNone(self.pre("Edit", file_path=str(self.repo / "tests/test_other.py"), old_string="a", new_string="b"))

    def test_reminders_are_factual_statements(self):
        text = self.context(self.pre("Read", file_path=str(self.repo / ".env")))
        self.assertTrue(text.startswith("doctrine-map: doctrine.toml routes `.env`"), text)
        self.assertNotRegex(text, r"(?i)\b(you must|always|ignore previous|system:)")

    def test_read_and_shell_triggers(self):
        self.assertIn('"secrets"', self.context(self.pre("Read", file_path=str(self.repo / ".env"))))
        self.assertIsNone(self.pre("Read", file_path=str(self.repo / "src/app.py")), "no read route covers it")
        self.assertIn('"migrations"', self.context(self.bash("psql -f db/migrations/001.sql")))
        self.assertIn('"tests"', self.context(self.bash("echo '# note' >> tests/test_app.py")), "a shell write is an edit")

    def test_shell_command_run_inside_a_routed_directory(self):
        (self.repo / "infra").mkdir()
        out = hooks.handle(dict(self.payload("PreToolUse", tool_name="Bash", tool_input={"command": "terraform plan"}),
                                cwd=str(self.repo / "infra")))
        self.assertIn('"infrastructure"', self.context(out))

    def test_paths_outside_the_project_get_nothing(self):
        self.assertIsNone(self.pre("Edit", file_path=str(self.base / "elsewhere.py"), old_string="a", new_string="b"))

    def test_compaction_allows_delivery_again(self):
        self.pre("Edit", file_path=str(self.repo / "tests/test_app.py"), old_string="a", new_string="b")
        hooks.handle(self.payload("SessionStart", source="compact"))
        self.assertIn('"tests"', self.context(self.pre("Edit", file_path=str(self.repo / "tests/test_app.py"), old_string="a", new_string="b")))


class RuleFiles(HookCase):
    def test_edit_to_rule_files_asks(self):
        for rel in ("CLAUDE.md", "AGENTS.md", "docs/AGENTS.md", ".claude/settings.json", "doctrine.toml",
                    ".doctrine/hooks.py", ".doctrine/sessions/x/receipts.jsonl"):
            with self.subTest(rel=rel):
                out = self.pre("Write", file_path=str(self.repo / rel), content="x")
                self.assertEqual(self.decision(out), "ask")
                self.assertIn("P15", self.reason(out))

    def test_ordinary_files_do_not_ask(self):
        self.assertEqual(self.decision(self.pre("Write", file_path=str(self.repo / "src/new.py"), content="x = 1\n")), "")

    def test_shell_writes_to_rule_files_ask_and_doctrine_build_does_not(self):
        self.assertEqual(self.decision(self.bash("echo 'be nice' >> AGENTS.md")), "ask")
        self.assertEqual(self.decision(self.bash("sed -i '' 's/a/b/' CLAUDE.md")), "ask")
        self.assertEqual(self.decision(self.bash("cp /tmp/x .claude/settings.json")), "ask")
        self.assertEqual(self.decision(self.bash("doctrine build")), "")
        self.assertEqual(self.decision(self.bash("cat CLAUDE.md")), "")


class Irreversible(HookCase):
    def test_force_push_asks_and_names_the_principle(self):
        out = self.bash("git push --force-with-lease origin main")
        self.assertEqual(self.decision(out), "ask")
        self.assertIn("replaces history on the remote", self.reason(out))
        self.assertIn("P2 (Ask before irreversible or publishing actions)", self.reason(out))

    def test_ordinary_push_is_silent(self):
        self.assertIsNone(self.bash("git push origin main"))

    def test_rm_of_the_repository_root(self):
        self.assertIn("the repository root", self.reason(self.bash("rm -rf .")))
        self.assertIsNone(self.bash("rm -rf src/__pycache__"))

    def test_cd_changes_what_relative_paths_mean(self):
        self.assertEqual(self.decision(self.bash("cd src && rm -rf ..")), "ask")


class BypassChecks(HookCase):
    def test_skipping_hooks_asks_and_names_the_principle(self):
        out = self.bash("git commit --no-verify -m wip")
        self.assertEqual(self.decision(out), "ask")
        self.assertIn("skips the hooks that run on commit", self.reason(out))
        self.assertIn("P1 (Leave the checks on)", self.reason(out))
        self.assertEqual(self.decision(self.bash("HUSKY=0 git push")), "ask")

    def test_mentions_are_not_bypasses(self):
        self.assertIsNone(self.bash('git commit -m "no-verify flag docs"'))
        self.assertIsNone(self.bash("grep -- --no-verify README.md"))


class Secrets(HookCase):
    def test_commit_with_staged_key_is_denied_without_echoing_it(self):
        self.write("src/settings.py", "REGION = 'eu'\nKEY = '" + fake_aws_key() + "'\n")
        self.git("add", "src/settings.py")
        out = self.bash("git commit -m 'add settings'")
        self.assertEqual(self.decision(out), "deny")
        self.assertIn("`src/settings.py` line 2 (an AWS access key)", self.reason(out))
        self.assertNotIn(fake_aws_key(), json.dumps(out))
        self.assertIn("P11", self.reason(out))

    def test_add_then_commit_in_one_command_scans_what_will_be_added(self):
        self.write("notes/token.txt", "token: " + fake_github_token() + "\n")
        self.assertEqual(self.decision(self.bash("git add -A && git commit -m wip")), "deny")

    def test_commit_all_scans_tracked_changes(self):
        self.write("src/app.py", "TOKEN = '" + fake_github_token() + "'\n")
        self.assertEqual(self.decision(self.bash("git commit -am wip")), "deny")
        self.assertIsNone(self.bash("git commit -m wip"), "nothing staged, so nothing to scan")

    def test_staged_env_file_is_denied_and_example_is_not(self):
        self.write(".env.example", "API_KEY=\n")
        self.git("add", ".env.example")
        self.assertIsNone(self.bash("git commit -m example"))
        self.write(".env", "API_KEY=abc\n")
        self.git("add", "-f", ".env")
        self.assertIn("an environment file", self.reason(self.bash("git commit -m env")))

    def test_write_with_key_shape_asks_unless_ignored(self):
        out = self.pre("Write", file_path=str(self.repo / "src/conf.py"), content="K = '" + fake_aws_key() + "'\n")
        self.assertEqual(self.decision(out), "ask")
        self.assertNotIn(fake_aws_key(), json.dumps(out))
        self.assertIsNone(self.pre("Write", file_path=str(self.repo / "local/creds.txt"), content=fake_aws_key()))
        same = "K = '" + fake_aws_key() + "'"
        self.assertEqual(self.decision(self.pre("Edit", file_path=str(self.repo / "src/conf.py"), old_string=same, new_string=same + "  # moved")), "")


class MaskedStatus(HookCase):
    def test_masked_test_command_is_noted_then_briefly(self):
        first = self.context(self.bash("pytest -q 2>&1 | tail -5"))
        self.assertIn("piped into `tail` without pipefail", first)
        self.assertIn("P5", first)
        second = self.context(self.bash("npm test || true"))
        self.assertIn("is hidden (followed by `|| true`)", second)
        self.assertNotIn("P5", second)

    def test_kept_status_is_silent(self):
        for command in ("set -o pipefail; pytest | tail -5", "pytest", "ls | head", "pytest; exit $?"):
            with self.subTest(command=command):
                self.assertIsNone(self.bash(command))


class PostTool(HookCase):
    def receipts(self):
        return [json.loads(line) for line in (self.repo / ".doctrine/sessions" / self.session / "receipts.jsonl").read_text().splitlines()]

    def test_receipts_record_class_exit_and_status(self):
        self.ran("pytest -q")
        self.ran("git push origin main", code=1)
        self.ran("ls")
        rows = self.receipts()
        self.assertEqual([(r["class"], r["exit"]) for r in rows], [("test", 0), ("git-push", 1), ("other", 0)])
        self.assertEqual(rows[1]["segments"][0]["status"], "failed")
        self.assertTrue(all(isinstance(r["ts"], float) for r in rows))

    def test_first_failure_is_noted_once(self):
        self.assertIn("exited 2", self.context(self.ran("pytest", code=2)))
        self.assertIsNone(self.ran("pytest", code=2))

    def test_unparseable_failure_and_interrupts_are_unknown(self):
        hooks.handle(self.payload("PostToolUseFailure", tool_name="Bash", tool_input={"command": "pytest"}, error="Command timed out"))
        hooks.handle(self.payload("PostToolUseFailure", tool_name="Bash", tool_input={"command": "pytest"}, error="Exit code 1", is_interrupt=True))
        self.post("Bash", {"interrupted": True}, command="pytest")
        self.ran("pytest", run_in_background=True)
        self.assertEqual([r["exit"] for r in self.receipts()], [None, None, None, None])
        self.assertEqual({r["segments"][0]["status"] for r in self.receipts()}, {"unknown"})

    def test_receipts_redact_key_shapes(self):
        self.ran("curl -H 'Authorization: " + fake_github_token() + "' https://example.org")
        self.assertNotIn(fake_github_token(), json.dumps(self.receipts()))

    def test_edit_ledger(self):
        self.post("Edit", file_path=str(self.repo / "src/app.py"), old_string="a", new_string="b")
        self.post("NotebookEdit", notebook_path=str(self.repo / "nb.ipynb"), new_source="x")
        self.post("Write", file_path=str(self.base / "outside.txt"), content="x")
        rows = (self.repo / ".doctrine/sessions" / self.session / "edits.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(r)["path"] for r in rows], ["src/app.py", "nb.ipynb"])

    def test_untrusted_content_note_once_per_tool(self):
        text = self.context(self.post("WebFetch", url="https://example.org"))
        self.assertIn("did not come from the person", text)
        self.assertIn("P12", text)
        self.assertIsNone(self.post("WebFetch", url="https://example.org/2"))
        self.assertIn("mcp__web__browse_page", self.context(self.post("mcp__web__browse_page", url="x")))
        self.assertIsNone(self.post("Read", file_path=str(self.repo / "src/app.py")))

    def test_session_record_never_dirties_the_tree(self):
        self.ran("pytest")
        self.post("Edit", file_path=str(self.repo / "src/app.py"), old_string="a", new_string="b")
        self.assertEqual(self.git("status", "--porcelain"), "")


class SessionStart(HookCase):
    def test_entry_card_after_compaction(self):
        text = self.context(hooks.handle(self.payload("SessionStart", source="compact")))
        self.assertIn("Doctrine: safety-core", text)
        self.assertIn("P6 [block]", text)

    def test_nothing_on_startup_by_default(self):
        self.assertIsNone(hooks.handle(self.payload("SessionStart", source="startup")))

    def test_old_session_records_are_pruned_on_startup(self):
        old = self.repo / ".doctrine/sessions/old-session"
        old.mkdir(parents=True)
        os.utime(old, (0, 0))
        hooks.handle(self.payload("SessionStart", source="startup"))
        self.assertFalse(old.exists())


class EntryOnStartup(HookCase):
    hooks_table = "entry_on_startup = true"

    def test_entry_card_on_startup_when_configured(self):
        self.assertIn("Doctrine: safety-core", self.context(hooks.handle(self.payload("SessionStart", source="startup"))))


class ModeOverrides(HookCase):
    hooks_table = 'irreversible = "block"\nmasked_status = "advise"\nreminders = "off"\nsecrets = "ask"\nrule_files = "off"'

    def test_modes(self):
        self.assertEqual(self.decision(self.bash("git push --force")), "deny")
        out = self.bash("pytest | tail")
        self.assertIn("piped into `tail`", out["systemMessage"])
        self.assertEqual(self.context(out), "")
        self.assertIsNone(self.pre("Edit", file_path=str(self.repo / "tests/test_app.py"), old_string="a", new_string="b"))
        self.assertIsNone(self.pre("Write", file_path=str(self.repo / "CLAUDE.md"), content="x"))
        self.write("src/k.py", "K = '" + fake_aws_key() + "'\n")
        self.git("add", "src/k.py")
        self.assertEqual(self.decision(self.bash("git commit -m k")), "ask")


class AllOff(HookCase):
    hooks_table = "\n".join(f'{check} = "off"' for check in hooks.CHECKS)

    def test_everything_off_is_silent_and_records_nothing(self):
        self.assertIsNone(self.bash("git push --force"))
        self.ran("pytest", code=1)
        self.assertIsNone(self.stop("Pushed. All tests pass. Should I proceed?"))
        self.assertFalse((self.repo / ".doctrine/sessions" / self.session / "receipts.jsonl").exists())


class DoctrineInsideDotDoctrine(HookCase):
    def setUp(self):
        super().setUp()
        (self.repo / ".doctrine").mkdir()
        (self.repo / "doctrine.toml").rename(self.repo / ".doctrine" / "doctrine.toml")

    def test_paths_are_relative_to_the_repository_not_the_doctrine_folder(self):
        self.assertIn('routes `tests/test_app.py` to "tests"',
                      self.context(self.pre("Edit", file_path=str(self.repo / "tests/test_app.py"), old_string="a", new_string="b")))
        self.assertEqual(self.decision(self.pre("Edit", file_path=str(self.repo / ".doctrine/doctrine.toml"), old_string="a", new_string="b")), "ask")
        self.ran("pytest")
        self.assertTrue((self.repo / ".doctrine/sessions" / self.session / "receipts.jsonl").is_file())


class InitLayout(HookCase):
    """A repository laid out the way `doctrine.py init` leaves it: everything under .doctrine/."""

    doctrine = False
    migration = {"command": "psql -f db/migrations/001.sql"}

    def run_command(self, argv, payload, **env):
        environ = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
        done = subprocess.run(argv, input=json.dumps(payload), capture_output=True, text=True, cwd=str(self.repo), env=dict(environ, **env))
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout) if done.stdout.strip() else None

    def test_vendored_copy_delivers_the_migrations_reminder(self):
        dot = self.repo / ".doctrine"
        dot.mkdir()
        for name in ("doctrine.toml", "doctrine.py", "hooks.py"):
            shutil.copyfile(ROOT / name, dot / name)
        out = self.run_command([sys.executable, str(dot / "hooks.py")], self.payload("PreToolUse", tool_name="Bash", tool_input=self.migration))
        self.assertIn('.doctrine/doctrine.toml routes `db/migrations/001.sql` to "migrations"', self.context(out))
        self.assertFalse((dot / "__pycache__").exists(), "no bytecode is written beside the vendored copy")

    def test_after_doctrine_py_init_the_wired_command_runs(self):
        done = subprocess.run([sys.executable, str(ROOT / "doctrine.py"), "init", "--target", str(self.repo)],
                              capture_output=True, text=True, cwd=str(self.repo))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        command = json.loads((self.repo / ".claude/settings.json").read_text())["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertIn(".doctrine/hooks.py", command)
        payload = self.payload("PreToolUse", tool_name="Bash", tool_input=self.migration)
        out = self.run_command(["sh", "-c", command], payload, CLAUDE_PROJECT_DIR=str(self.repo))
        self.assertIn('routes `db/migrations/001.sql` to "migrations"', self.context(out))


class NoDoctrine(HookCase):
    doctrine = False

    def test_without_a_doctrine_the_hooks_do_nothing(self):
        self.assertIsNone(self.bash("git push --force"))
        self.assertIsNone(self.ran("pytest", code=1))
        self.assertIsNone(self.stop("Pushed."))
        self.assertFalse((self.repo / ".doctrine").exists())


class BrokenDoctrine(HookCase):
    hooks_table = 'irreversible = "block"\n[[principle]]\nid = "P99"'

    def test_an_invalid_doctrine_keeps_the_guards_at_their_configured_levels(self):
        out = self.bash("git push --force")
        self.assertEqual(self.decision(out), "deny")
        self.assertNotIn("Principle", self.reason(out))


class Script(HookCase):
    def test_runs_as_a_script_with_json_on_stdin(self):
        code, out, err = self.script(self.payload("PreToolUse", tool_name="Bash", tool_input={"command": "git reset --hard"}))
        self.assertEqual(code, 0, err)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_event_from_argv(self):
        payload = self.payload("SessionStart", source="compact")
        del payload["hook_event_name"]
        code, out, _ = self.script(payload, "SessionStart")
        self.assertIn("Doctrine: safety-core", out["hookSpecificOutput"]["additionalContext"])

    def test_bad_input_exits_zero_with_one_line_on_stderr(self):
        code, out, err = self.script(None, raw="{not json")
        self.assertEqual((code, out), (0, None))
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("doctrine-map hooks:", err)

    def test_no_doctrine_is_silent(self):
        code, out, err = self.script({"hook_event_name": "Stop", "cwd": str(self.base), "last_assistant_message": "Pushed."})
        self.assertEqual((code, out, err), (0, None, ""))

    def test_old_python_says_so_once_at_session_start(self):
        stdin, stdout = io.StringIO(json.dumps(self.payload("SessionStart", source="startup"))), io.StringIO()
        with mock.patch.object(sys, "version_info", (3, 9, 6)), mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", stdout):
            hooks.main(["hooks.py"])
        self.assertIn("need Python 3.11", json.loads(stdout.getvalue())["systemMessage"])


class Wiring(unittest.TestCase):
    def test_checks_is_a_literal_with_the_agreed_shape(self):
        tree = ast.parse((ROOT / "hooks.py").read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CHECKS" for t in n.targets))
        checks = ast.literal_eval(node.value)
        self.assertEqual(set(checks), {"reminders", "rule_files", "masked_status", "irreversible", "bypass_checks", "secrets", "receipts",
                                       "edit_ledger", "untrusted_content", "unsupported_claim", "permission_gate", "dirty_tree",
                                       "unlogged_mistake", "entry_card"})
        for check, spec in checks.items():
            self.assertEqual(set(spec), {"principles", "level", "event"}, check)
            self.assertIn(spec["event"], hooks.WIRING, check)

    def test_principles_named_by_checks_exist_in_the_reference_doctrine(self):
        doctrine = hooks._api().load(ROOT / "doctrine.toml")
        for check, spec in hooks.CHECKS.items():
            for pid in spec["principles"]:
                self.assertIn(pid, doctrine.principles, check)

    def test_plugin_hooks_json_matches_the_wiring(self):
        data = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        command = 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks.py"'
        expected = {event: [dict({"matcher": matcher} if matcher else {}, hooks=[{"type": "command", "command": command, "timeout": timeout}])]
                    for event, (matcher, timeout) in hooks.WIRING.items()}
        self.assertEqual(data, {"hooks": expected})


if __name__ == "__main__":
    unittest.main()
