"""Reading shell commands: the lexer, the exit-status model, command classes and the small guards."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_hooks_support import fake_aws_key, fake_github_token, fake_private_key_header, hooks  # noqa: E402


def words(command):
    return [c["words"] for c in hooks.commands(command)]


def model(command):
    return [(m["head"], m["vis"]) for m in hooks.exit_model(command)]


class Lexer(unittest.TestCase):
    def test_operators_only_outside_quotes(self):
        self.assertEqual(words('echo ";" | tail'), [["echo", ";"], ["tail"]])
        self.assertEqual(words("find . -exec rm {} \\;"), [["find", ".", "-exec", "rm", "{}", ";"]])
        self.assertEqual(words('git commit -m "a | b && c"'), [["git", "commit", "-m", "a | b && c"]])
        self.assertEqual(words("pytest;\nls"), [["pytest"], ["ls"]])

    def test_redirections(self):
        cmds = hooks.commands("pytest 2>&1 >out.log | tee -a all.log &>/dev/null")
        self.assertEqual(cmds[0]["words"], ["pytest"])
        self.assertEqual(cmds[0]["writes"], ["out.log"])
        self.assertEqual(cmds[0]["op"], "|")
        self.assertEqual(hooks.commands("cmd &>both.log")[0]["writes"], ["both.log"])
        self.assertEqual(hooks.commands("cmd >> 'a b.txt'")[0]["writes"], ["a b.txt"])

    def test_comments_and_heredocs_are_not_commands(self):
        self.assertEqual(words("# git push --force\npytest"), [["pytest"]])
        self.assertEqual(words("cat <<'EOF' > notes.md\ngit push --force\nEOF\nls"), [["cat"], ["ls"]])
        self.assertEqual(words("echo a#b"), [["echo", "a#b"]])

    def test_substitutions_stay_in_their_word(self):
        self.assertEqual(words("echo $(git rev-parse HEAD) `date`"), [["echo", "$(git rev-parse HEAD)", "`date`"]])

    def test_nesting(self):
        cmds = hooks.commands("if pytest; then echo ok; fi; (cd x && make); git push")
        self.assertEqual([(c["words"][0], c["nested"]) for c in cmds], [("pytest", True), ("echo", True), ("cd", True), ("make", True), ("git", False)])

    def test_bash_c_bodies_are_read_for_guards(self):
        inner = [c for c in hooks.commands("bash -c 'git push --force'") if c["inner"]]
        self.assertEqual(inner[0]["words"], ["git", "push", "--force"])

    def test_unbalanced_quotes_do_not_raise(self):
        self.assertTrue(hooks.commands('echo "unterminated'))


class Classes(unittest.TestCase):
    def test_kinds(self):
        cases = {
            "pytest -q": "test", "python3 -m pytest tests": "test", "python -m unittest discover": "test", "tox -e py311": "test",
            "npm test": "test", "npm run test -- --watch=false": "test", "pnpm test:unit": "test", "yarn build": "build",
            "bun run build": "build", "npx jest": "test", "npx vitest run": "test", "cargo test": "test", "cargo build --release": "build",
            "go test ./...": "test", "go build ./cmd/x": "build", "make": "build", "make test": "test", "./gradlew check": "test",
            "mvn package": "build", "dotnet test": "test", "bundle exec rspec": "test", "vendor/bin/phpunit": "test",
            "uv run pytest": "test", "timeout 600 pytest": "test", "CI=1 sudo -u ci npm test": "test", "./scripts/test.sh": "test",
            "git commit -m x": "git-commit", "git -C repo push": "git-push", "git pull --rebase": "git", "git status": None,
            "ls -la": None, "npm install": None, "python script.py": None, "make -n": "build",
        }
        for command, kind in cases.items():
            with self.subTest(command=command):
                self.assertEqual(hooks.kind_of(hooks.commands(command)[0]["words"]), kind)


class ExitModel(unittest.TestCase):
    def test_masked(self):
        for command in ("pytest | tail -5", "pytest 2>&1 | grep FAIL", "pytest || true", "pytest || echo failed",
                        "pytest; echo done", "pytest &", "! pytest", "npm test | tee log.txt", "git push 2>&1 | tail -3",
                        "set -o pipefail; set +o pipefail; pytest | tail", "pytest; if x; then y; fi"):
            with self.subTest(command=command):
                self.assertEqual(model(command)[0][1], "masked")

    def test_kept(self):
        for command in ("pytest", "cd web && npm test", "set -o pipefail; pytest | tail", "set -euo pipefail\npytest | tail -5",
                        "setopt pipefail; pytest | tail", "pytest || exit 1", "pytest; exit $?", "set -e; pytest; echo done",
                        "pytest && git push", "pytest | tee out.log; exit ${PIPESTATUS[0]}", "pytest || false"):
            with self.subTest(command=command):
                self.assertEqual({vis for _, vis in model(command)}, {"kept"})

    def test_captured_or_unknown(self):
        self.assertEqual(model("pytest; echo $?"), [("pytest", "captured")])
        self.assertEqual(model("pytest || echo \"failed with $?\""), [("pytest", "captured")])
        self.assertEqual(model("if pytest; then echo ok; fi"), [("pytest", "unknown")])
        self.assertEqual(model("(pytest)"), [("pytest", "unknown")])
        self.assertEqual(model("bash -c 'pytest | tail'"), [])

    def test_quiet_for_non_critical_pipes(self):
        self.assertEqual(model("ls | head"), [])
        self.assertEqual(model("git log --oneline | head -5"), [])
        self.assertEqual(model("cat pytest.ini | grep x"), [])

    def test_statuses(self):
        self.assertEqual(hooks.statuses("pytest", 0, False), [{"kind": "test", "head": "pytest", "status": "ok"}])
        self.assertEqual(hooks.statuses("pytest", 1, False)[0]["status"], "failed")
        self.assertEqual(hooks.statuses("pytest", None, False)[0]["status"], "unknown")
        self.assertEqual(hooks.statuses("pytest", 0, True)[0]["status"], "unknown")
        self.assertEqual(hooks.statuses("pytest | tail", 0, False)[0]["status"], "masked")
        self.assertEqual(hooks.statuses("pytest; echo $?", 0, False)[0]["status"], "unknown")
        both = hooks.statuses("pytest && git push", 1, False)
        self.assertEqual([s["status"] for s in both], ["unknown", "failed"], "the failure is pinned on the last command only")
        self.assertEqual([s["status"] for s in hooks.statuses("pytest && git push", 0, False)], ["ok", "ok"])
        self.assertEqual(hooks.statuses("pytest && cp report.xml /nowhere", 1, False)[0]["status"], "unknown")
        self.assertEqual(hooks.statuses("ls cache || pytest", 0, False)[0]["status"], "unknown", "may not have run")
        self.assertEqual([s["status"] for s in hooks.statuses("make lint || pytest", 0, False)], ["masked", "unknown"])
        self.assertEqual(hooks.statuses("set -o pipefail; pytest | tail", 2, False)[0]["status"], "failed")


class Guards(unittest.TestCase):
    root = Path("/work/project")

    def guard(self, command, cwd=None):
        return [hooks.irreversible(c["words"], cwd or self.root, self.root) for c in hooks.commands(command)]

    def asks(self, command, cwd=None):
        return any(self.guard(command, cwd))

    def test_irreversible_commands_ask(self):
        for command in ("git push --force origin main", "git push -f", "git push --force-with-lease", "git push -uf origin x",
                        "git push origin +main", "git push --mirror", "git push origin --delete old", "git push origin :old",
                        "git reset --hard HEAD~1", "git branch -D old", "git branch --delete --force old", "git clean -fdx",
                        "git clean -f", "rm -rf /", "rm -rf ~", "rm -rf $HOME", "rm -rf ~/projects/other", "sudo rm -rf /",
                        "rm -rf .", "rm -r ..", "rm -rf *", "rm -rf .git", "rm -rf /usr/local/share/thing",
                        "terraform destroy", "terraform apply -destroy -auto-approve", "tofu destroy", "npm publish",
                        "pnpm publish --access public", "yarn npm publish", "twine upload dist/*", "python3 -m twine upload dist/*",
                        "cargo publish", "poetry publish --build", "uv publish", "gem push x.gem",
                        "gh repo create demo --public", "gh repo edit --visibility public", "gh repo edit --visibility=public"):
            with self.subTest(command=command):
                self.assertTrue(self.asks(command))

    def test_reversible_commands_pass(self):
        for command in ("git push origin main", "git push -u origin feature", "git push --dry-run --force", "git push -n -f",
                        "git reset --soft HEAD~1", "git reset HEAD file", "git branch -d merged", "git clean -n", "git clean -fn",
                        "rm -rf build", "rm -rf ./node_modules", "rm file.txt", "rm -f ../notes.txt", "rm -rf \"$BUILD_DIR\"",
                        "rm -rf /tmp/scratch-dir", "terraform plan", "terraform apply", "npm publish --dry-run", "npm run publish-docs",
                        "cargo publish --dry-run", "gh repo create demo --private", "gh repo view", "echo 'git push --force'",
                        "git commit -m 'never git push --force'", "git log --force", "ls -la"):
            with self.subTest(command=command):
                self.assertFalse(self.asks(command))

    def test_publish_dry_run_must_be_enabled(self):
        # These are parser input only: no publisher is launched.
        for command in ("npm publish --dry-run=false", "npm publish --dry-run false",
                        "npm publish --dry-run --no-dry-run", "npm publish --dry-run --dry-run=false",
                        "npm publish --dry-run --no-dry-run=true",
                        "npm publish -- --dry-run", "npm publish -n", "poetry publish -n",
                        "twine upload -n dist/*", "python3 -m twine upload -n dist/*",
                        "twine upload --dry-run dist/*", "gem push -n demo.gem"):
            with self.subTest(command=command):
                self.assertTrue(self.asks(command), command)
        for command in ("npm publish --dry-run", "npm publish --dry-run=true",
                        "npm publish --dry-run true", "npm publish --dry-run=false --dry-run",
                        "npm publish --dry-run --no-dry-run=false",
                        "pnpm publish --dry-run", "yarn npm publish --dry-run", "bun publish --dry-run",
                        "cargo publish --dry-run", "poetry publish --dry-run", "uv publish --dry-run"):
            with self.subTest(command=command):
                self.assertFalse(self.asks(command), command)

    def test_relative_targets_use_the_cd_and_cwd(self):
        self.assertTrue(self.asks("rm -rf ..", cwd=self.root / "sub"), "the repository root from a subdirectory")
        self.assertFalse(self.asks("rm -rf old", cwd=self.root / "sub"))

    def test_descriptions_name_what_happens(self):
        self.assertIn("replaces history on the remote", self.guard("git push --force")[0])
        self.assertIn("the home directory", self.guard("rm -rf ~")[0])
        self.assertIn("the repository root", self.guard("rm -rf .")[0])
        self.assertIn("ignored files", self.guard("git clean -fdx")[0])


class Bypass(unittest.TestCase):
    def skip(self, command):
        cmds = hooks.commands(command)
        runs_hooks = any(hooks.kind_of(c["words"]) in ("git-commit", "git-push") or hooks.head_of(c["words"]) == "pre-commit"
                         or hooks.label(c["words"]) == "git merge" for c in cmds)
        return [hooks.bypass(c["words"], runs_hooks) for c in cmds]

    def test_commands_that_skip_or_disable_checks(self):
        for command in ("git commit --no-verify -m wip", "git push --no-verify", "git merge --no-verify feature",
                        "git commit -n -m wip", "git commit -nm wip", "git commit -anm wip", "git commit -m wip -n",
                        "git -C repo commit --no-verify", "HUSKY=0 git commit -m wip", "export HUSKY=0",
                        "SKIP=flake8 git commit -m wip", "SKIP=mypy pre-commit run --all-files", "export SKIP=flake8; git commit -m x",
                        "git config core.hooksPath /dev/null", "git config --global core.hooksPath .nohooks",
                        "git config --unset core.hooksPath", "git config set core.hooksPath x", "git config unset core.hooksPath",
                        "git -c core.hooksPath=/dev/null commit -m wip", "pre-commit uninstall", "sudo pre-commit uninstall -t pre-push"):
            with self.subTest(command=command):
                self.assertTrue(any(self.skip(command)))

    def test_commands_that_leave_checks_on(self):
        for command in ('git commit -m "no-verify flag docs"', "grep -- --no-verify README.md", "git commit -m -n",
                        "git commit -mn", "git commit -F notes.txt", "git commit -S -m signed", "git push -n origin main",
                        "git merge -n feature", "git log --no-verify", "git commit --no-gpg-sign -m x",
                        "git config core.hooksPath", "git config --get core.hooksPath", "HUSKY=1 git commit -m x",
                        "SKIP=1 make deploy", "pre-commit run --all-files", "pre-commit install", "echo HUSKY=0",
                        "git commit -m wip -- -n"):
            with self.subTest(command=command):
                self.assertFalse(any(self.skip(command)))

    def test_descriptions(self):
        self.assertIn("skips the hooks that run on commit (--no-verify)", self.skip("git commit --no-verify")[0])
        self.assertIn("HUSKY=0", self.skip("HUSKY=0 git push")[0])
        self.assertIn("core.hooksPath", self.skip("git config core.hooksPath /dev/null")[0])


class Secrets(unittest.TestCase):
    def test_shapes(self):
        self.assertEqual(hooks.shapes("key = '" + fake_aws_key() + "'"), ["an AWS access key"])
        self.assertEqual(hooks.shapes(fake_github_token()), ["a GitHub token"])
        self.assertEqual(hooks.shapes(fake_private_key_header()), ["a private key block"])
        self.assertEqual(hooks.shapes("password = 'correct horse battery staple'"), [], "generic passwords are too noisy")
        self.assertEqual(hooks.shapes("sha = 3f786850e387550fdab836ed7e6dc881de23001b"), [])

    def test_redaction(self):
        self.assertNotIn(fake_aws_key(), hooks.SECRET_RE.sub("[redacted]", "export K=" + fake_aws_key()))

    def test_env_files(self):
        for name in (".env", "app/.env", ".env.local", ".env.production"):
            self.assertTrue(hooks.env_file(name), name)
        for name in (".env.example", ".env.sample", ".env.template", "env.py", ".envrc.md"):
            self.assertFalse(hooks.env_file(name), name)


if __name__ == "__main__":
    unittest.main()
