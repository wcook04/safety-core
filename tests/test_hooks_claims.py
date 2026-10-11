"""The Stop claim check: which sentences are claims, what contradicts them, and how Stop answers."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_hooks_support import HookCase, hooks  # noqa: E402

CLAIMS = [
    ("I pushed the branch to origin.", {"pushed"}),
    ("Pushed.", {"pushed"}),
    ("Committed and pushed.", {"committed", "pushed"}),
    ("The changes are committed and pushed to origin/main.", {"committed", "pushed"}),
    ("Force-pushed the rebased branch.", {"pushed"}),
    ("The push succeeded.", {"pushed"}),
    ("All tests pass.", {"tests_pass"}),
    ("The test suite passes.", {"tests_pass"}),
    ("Tests are passing now.", {"tests_pass"}),
    ("pytest passes.", {"tests_pass"}),
    ("42 passed in 3.1s.", {"tests_pass"}),
    ("Unit tests pass locally.", {"tests_pass"}),
    ("Working tree is clean.", {"clean"}),
    ("The working tree is clean and everything is committed.", {"clean", "committed"}),
    ("git status is clean.", {"clean"}),
    ("Nothing to commit.", {"clean"}),
    ("There are no uncommitted changes.", {"clean"}),
    ("I made a commit with the fix.", {"committed"}),
    ("Done: committed as abc1234.", {"committed"}),
    ("Committed to main.", {"committed"}),
    ("I committed the fix to the feature branch.", {"committed"}),
    ("The tests passed and I pushed.", {"tests_pass", "pushed"}),
    ('Final state is "clean-and-pushed" for the repo.', {"pushed"}),
    ("Should I push? Tests pass.", {"tests_pass"}),
    ("- [x] pushed the fix", {"pushed"}),
    ("I can see the branch is pushed.", {"pushed"}),
    # realistic end-of-turn summaries
    ("## Summary\n- Fixed the off-by-one in `parse()`\n- Added a regression test\n\nAll 42 tests pass.", {"tests_pass"}),
    ("Changes committed (abc1234) and pushed to `feature/x`.", {"committed", "pushed"}),
    ("Before pushing, I ran the full suite: 120 passed.", {"tests_pass"}),
    ("I pushed the fix, but CI is still running, so I can't confirm the tests pass on CI.", {"pushed"}),
    ("Tests: 15 passed, 2 skipped.", {"tests_pass"}),
    ("Committed to a branch called fix/parser; not pushed.", {"committed"}),
    ("Status: committed ✅", {"committed"}),
    ("I ran `npm test` and all tests pass.", {"tests_pass"}),
    ("The branch was already pushed earlier today.", {"pushed"}),
    ("Nothing to commit, working tree clean.", {"clean"}),
    ("Here is the diff of what I committed.", {"committed"}),
    ("Tests pass on main and on the release branch.", {"tests_pass"}),
    ("I pushed the commits to origin.", {"pushed"}),
    ("The database migration is committed and pushed.", {"pushed"}),
]

NOT_CLAIMS = [
    "I have not pushed yet.",
    "Nothing was pushed.",
    "The branch has not been pushed.",
    "I haven't committed or pushed anything.",
    "I haven’t pushed the branch.",
    "Not pushed: the remote rejected it.",
    "Pushed: no",
    "- Pushed: pending",
    "| Pushed | No |",
    "Tests passed: 0",
    "Do the tests pass?",
    "Have you pushed?",
    "Is the working tree clean?",
    "Tests pass, right?",
    "Once the tests pass, I will push.",
    "If the tests pass, commit it.",
    "Make sure the tests pass before merging.",
    "It will be pushed when CI is green.",
    "It needs to be committed.",
    "Ready to be pushed once you approve.",
    "You pushed it earlier.",
    "They committed the fix yesterday.",
    "When I pushed, the remote rejected it.",
    "I would have pushed, but the remote was down.",
    "Before this change, the tests passed.",
    "Previously all tests passed.",
    "Changes are staged but not committed.",
    "Nothing has been committed.",
    "The working tree is not clean.",
    "Keep the working tree clean.",
    "No tests pass.",
    "Not all tests pass.",
    "The tests don't pass yet.",
    "Tests pass rate improved to 80 percent.",
    "3 tests failed, 0 passed.",
    'The phrase "tests pass" is an example of a claim.',
    "The detector flags words like `pushed` and `committed`.",
    'Do not say "pushed" until it is.',
    'Saying "committed" here would be false.',
    "```\n$ git push\nEverything up-to-date\nall tests pass\n```",
    "> pushed to origin by someone else",
    "- [ ] push and confirm the tests pass",
    "I pushed back on that design.",
    "I'm committed to getting this right.",
    "I committed to this approach early on.",
    "See https://example.com/pushed-items for details.",
    "The file docs/pushed.md describes the flow.",
    "Uncommitted changes remain in src/app.py.",
    "There are unpushed commits on the branch.",
    "Run the tests and check that they pass.",
    "We expect the tests to pass.",
    "Whether it was pushed is unclear.",
    "It may have been pushed by CI.",
    "e.g. 'pushed' is a claim word.",
    # realistic end-of-turn summaries
    "I've updated `src/app.py` to handle the edge case and added a test. Run `pytest` to verify.",
    "The PR is ready. I haven't pushed it since you asked to review first.",
    "Note: the working tree has uncommitted changes from before this session.",
    "Let me know if you want me to push.",
    "The build passes and lint is clean.",
    "I didn't commit anything; the changes are in your working tree for review.",
    "Once you're happy, I can commit and push.",
    "This should make the tests pass.",
    "The commit message says 'fix: tests pass on CI'.",
    "Status: committed ❌, pushed ❌",
    "❌ pushed",
    "| Pushed | ❌ |",
    "No, I haven't pushed.",
    "Not yet committed or pushed.",
    "Unable to push: permission denied.",
    "Push failed: rejected (non-fast-forward).",
    "I tried to push, but it was rejected.",
    "Do you want me to commit these changes?",
    "I've staged the changes but not committed them.",
    "As requested, nothing has been pushed.",
    "The previous agent claimed the tests pass, but I found two failures.",
    "Should be pushed by now.",
    "I believe the tests pass, but I could not run them.",
    "I reviewed the committed changes and found a bug.",
    "The last commit was committed by Alice.",
    "I compared it with the pushed branch.",
    "CI is green.",
    "I pushed the validation down into the parser.",
    "I pushed the check into a helper so both callers share it.",
    "I pushed version 1.2 to PyPI.",
    "The image was pushed to the registry.",
    "The handler ensures the transaction is committed before replying.",
    "Kafka offsets are committed after each batch.",
    "The tests pass a fake clock to the scheduler.",
    "These tests pass the config through the fixture.",
]


class FindClaims(unittest.TestCase):
    def test_claims_are_found(self):
        for message, kinds in CLAIMS:
            with self.subTest(message=message):
                self.assertEqual({k for k, _ in hooks.find_claims(message)}, kinds)

    def test_non_claims_are_dropped(self):
        for message in NOT_CLAIMS:
            with self.subTest(message=message):
                self.assertEqual(hooks.find_claims(message), [])

    def test_a_negation_in_another_clause_does_not_cancel_a_claim(self):
        self.assertEqual({k for k, _ in hooks.find_claims("Tests pass locally, but I have not pushed.")}, {"tests_pass"})
        self.assertEqual({k for k, _ in hooks.find_claims("I did not run the linter, but the tests pass.")}, {"tests_pass"})

    def test_a_negation_further_than_five_words_back_does_not_cancel(self):
        self.assertEqual({k for k, _ in hooks.find_claims("Tests did not fail and now the branch is pushed.")}, {"pushed"})

    def test_names_failure(self):
        for text in ("41 passed, 1 failed", "test_x fails on Windows", "two failures remain", "the build is broken"):
            self.assertTrue(hooks.names_failure(text), text)
        for text in ("all tests pass with no failures", "0 failed", "zero test failures", "nothing failed", "done"):
            self.assertFalse(hooks.names_failure(text), text)

    def test_names_path(self):
        self.assertTrue(hooks.names("I left src/app.py uncommitted.", "src/app.py"))
        self.assertTrue(hooks.names("app.py is still modified", "src/app.py"))
        self.assertFalse(hooks.names("happy.py changed", "src/app.py"))
        self.assertFalse(hooks.names("a is changed", "src/a"))

    def test_self_errors(self):
        for text in ("I was wrong about the count.", "My mistake: the file is in src.", "I accidentally deleted the fixture.",
                     "I misread the error.", "I should not have run that."):
            self.assertTrue(hooks.self_errors(text), text)
        for text in ("If I was wrong about the path, say so.", "I broke the task into three steps.", "Was I wrong?",
                     'The phrase "my mistake" is detected.', "Everything went as planned."):
            self.assertEqual(hooks.self_errors(text), [], text)

    def test_permission_gates(self):
        self.assertTrue(hooks.permission_gates("Done with the first file. Should I proceed?"))
        self.assertTrue(hooks.permission_gates("Want me to continue with the remaining files?"))
        self.assertEqual(hooks.permission_gates("This will force-push over the remote history; should I proceed?"), [])
        self.assertEqual(hooks.permission_gates("Which option do you prefer? Should I proceed with A?"), [])
        self.assertEqual(hooks.permission_gates("Would you like me to also add tests?"), [])
        self.assertEqual(hooks.permission_gates("Let me know if you have questions."), [])


def gitstate(**kw):
    state = {"oid": "abc", "branch": "main", "upstream": "origin/main", "ahead": 0, "dirty": [], "prefix": "",
             "remotes": True, "on_remote": True, "root": None}
    state.update(kw)
    return state


def record(**kw):
    rec = {"push": None, "push_ok": False, "test": None, "logged": False, "edited": [], "edited_now": []}
    rec.update(kw)
    return rec


class Judge(unittest.TestCase):
    def hard(self, message, gitst, rec, receipts=True):
        return [text for _, text in hooks.judge(message, gitst, rec, receipts)[0]]

    def advice(self, message, gitst, rec, check="unsupported_claim"):
        return hooks.judge(message, gitst, rec)[1][check]

    def test_pushed_while_ahead(self):
        out = self.hard("Pushed.", gitstate(ahead=2, on_remote=False), record())
        self.assertEqual(len(out), 1)
        self.assertIn("2 commits ahead of `origin/main`", out[0])

    def test_pushed_when_head_is_on_a_remote_branch(self):
        self.assertEqual(self.hard("Pushed.", gitstate(ahead=2, on_remote=True), record()), [])

    def test_pushed_without_upstream(self):
        no_up = gitstate(upstream="", ahead=None, on_remote=False)
        self.assertIn("no upstream", self.hard("Pushed.", no_up, record())[0])
        self.assertEqual(self.hard("Pushed.", no_up, record(push_ok=True)), [])
        self.assertEqual(self.hard("Pushed.", no_up, record(), receipts=False), [])

    def test_pushed_after_a_failed_push(self):
        out = self.hard("Pushed.", gitstate(), record(push={"status": "failed", "exit": 1, "head": "git"}))
        self.assertIn("did not succeed", out[0])

    def test_pushed_without_a_remote(self):
        out = self.hard("Pushed.", gitstate(remotes=False, on_remote=False, upstream=""), record())
        self.assertIn("no remote", out[0])

    def test_committed_with_unnamed_dirty_edits(self):
        state = gitstate(dirty=["src/app.py", "notes.md"])
        out = self.hard("Committed the fix.", state, record(edited=["src/app.py"]))
        self.assertEqual(len(out), 1)
        self.assertIn("src/app.py", out[0])
        self.assertNotIn("notes.md", out[0])
        self.assertEqual(self.hard("Committed the fix; src/app.py is left for review.", state, record(edited=["src/app.py"])), [])

    def test_untracked_directories_count_as_dirty(self):
        out = self.hard("Everything is committed.", gitstate(dirty=["newdir/"]), record(edited=["newdir/a.py"]))
        self.assertIn("newdir/a.py", out[0])

    def test_naming_an_untracked_folder_names_what_is_in_it_but_a_tracked_folder_does_not(self):
        untracked = gitstate(dirty=["dist/"])
        self.assertEqual(self.hard("Everything is committed except the build output in dist/.", untracked, record(edited=["dist/app.js"])), [])
        tracked = gitstate(dirty=["src/other.py"])
        self.assertTrue(self.hard("Committed the changes in src/.", tracked, record(edited=["src/other.py"])))

    def test_paths_are_matched_through_the_doctrine_folder_prefix(self):
        state = gitstate(dirty=["pkg/src/app.py"], prefix="pkg/")
        self.assertIn("src/app.py", self.hard("Committed.", state, record(edited=["src/app.py"]))[0])

    def test_clean_with_only_foreign_changes_is_advice(self):
        state = gitstate(dirty=["other.txt"])
        self.assertEqual(self.hard("Working tree is clean.", state, record(edited=["src/app.py"])), [])
        self.assertIn("other.txt", self.advice("Working tree is clean.", state, record(edited=["src/app.py"]))[0])

    def test_tests_pass_after_a_failure(self):
        failed = record(test={"status": "failed", "exit": 1, "head": "pytest", "ts": 1})
        self.assertIn("exited 1", self.hard("All tests pass.", None, failed)[0])
        self.assertEqual(self.hard("All tests pass except test_x, which fails.", None, failed), [])
        self.assertEqual(self.hard("All tests pass.", None, record(test={"status": "ok", "exit": 0, "head": "pytest"})), [])

    def test_tests_pass_without_evidence_is_advice(self):
        self.assertIn("no recognised test command", self.advice("All tests pass.", None, record())[0])
        masked = record(test={"status": "masked", "exit": 0, "head": "pytest"})
        self.assertIn("hidden by the shell", self.advice("All tests pass.", None, masked)[0])
        self.assertEqual(hooks.judge("All tests pass.", None, record(), False)[1]["unsupported_claim"], [])

    def test_dirty_tree_advice_covers_this_turn_only(self):
        state = gitstate(dirty=["src/app.py", "old.py"])
        rec = record(edited=["src/app.py", "old.py"], edited_now=["src/app.py"])
        self.assertIn("src/app.py", self.advice("Here is the summary.", state, rec, "dirty_tree")[0])
        self.assertNotIn("old.py", self.advice("Here is the summary.", state, rec, "dirty_tree")[0])
        self.assertEqual(self.advice("I changed src/app.py and left it for review.", state, rec, "dirty_tree"), [])

    def test_unlogged_mistake(self):
        self.assertTrue(self.advice("My mistake: wrong path.", None, record(), "unlogged_mistake"))
        self.assertEqual(self.advice("My mistake: wrong path.", None, record(logged=True), "unlogged_mistake"), [])

    def test_no_claims_no_findings(self):
        hard, advice = hooks.judge("I read the code and wrote a plan.", gitstate(ahead=3, on_remote=False), record())
        self.assertEqual(hard, [])
        self.assertFalse(any(advice.values()))


class StopEndToEnd(HookCase):
    remote = True

    def commit_locally(self):
        self.write("src/app.py", "def add(a, b):\n    return b + a\n")
        self.git("commit", "-q", "-am", "local change")

    def test_pushed_while_ahead_blocks_once(self):
        self.commit_locally()
        out = self.stop("Committed and pushed to origin.")
        self.assertEqual(out["decision"], "block")
        self.assertIn("1 commit ahead of `origin/main`", out["reason"])
        self.assertIn("P6", out["reason"])
        again = self.stop("Committed and pushed to origin.", stop_hook_active=True)
        self.assertNotIn("decision", again)
        self.assertIn("ahead", again["systemMessage"])
        third = self.stop("Committed and pushed to origin.")
        self.assertNotIn("decision", third)

    def test_stop_hook_active_never_blocks_and_does_not_use_up_the_block(self):
        self.commit_locally()
        self.assertNotIn("decision", self.stop("Pushed.", stop_hook_active=True))
        self.assertEqual(self.stop("Pushed.")["decision"], "block")

    def test_real_push_clears_the_claim(self):
        self.commit_locally()
        self.git("push", "-q")
        self.ran("git push")
        self.assertIsNone(self.stop("Pushed."))

    def test_negated_claim_is_silent(self):
        self.commit_locally()
        self.assertIsNone(self.stop("Committed locally; I have not pushed yet."))

    def test_failed_push_receipt_blocks(self):
        self.ran("git push origin main", code=1)
        out = self.stop("Pushed to origin.")
        self.assertIn("did not succeed", out["reason"])

    def test_tests_pass_after_failure_blocks(self):
        self.ran("python -m pytest -q", code=1)
        out = self.stop("All tests pass.")
        self.assertIn("exited 1", out["reason"])
        self.assertIsNone(self.stop("All tests pass apart from test_slow, which fails on this machine."))

    def test_tests_pass_after_a_masked_run_is_advice(self):
        self.ran("pytest -q 2>&1 | tail -5")
        out = self.stop("All tests pass.")
        self.assertNotIn("decision", out)
        self.assertIn("hidden by the shell", out["systemMessage"])

    def test_committed_with_dirty_edit_blocks_and_naming_clears(self):
        self.edited("src/app.py")
        out = self.stop("Committed the fix.")
        self.assertIn("src/app.py", out["reason"])
        self.git("commit", "-q", "-am", "fix")
        self.assertIsNone(self.stop("Committed the fix."))

    def test_dirty_tree_advice(self):
        self.edited("src/app.py")
        out = self.stop("Here is what I found.")
        self.assertNotIn("decision", out)
        self.assertIn("src/app.py", out["systemMessage"])
        self.assertIsNone(self.stop("Here is what I found."), "advice covers edits made since the last stop")

    def test_permission_gate_and_mistake_advice(self):
        out = self.stop("My mistake: I misread the path. Should I proceed?")
        self.assertNotIn("decision", out)
        self.assertIn("admits a mistake", out["systemMessage"])
        self.assertIn("asks to go on", out["systemMessage"])
        self.ran("doctrine log-error --what 'misread the path'")
        self.assertNotIn("admits a mistake", (self.stop("My mistake: I misread the path.") or {}).get("systemMessage", ""))

    def test_a_mistake_logged_this_session_through_the_mistakes_log_counts(self):
        self.assertIn("admits a mistake", self.stop("I was wrong about the path.")["systemMessage"])
        (self.repo / ".doctrine" / "mistakes.jsonl").write_text('{"what": "wrong path"}\n')
        self.assertIsNone(self.stop("I was wrong about the path."))

    def test_two_contradictions_block_together_and_cite_the_principle_once(self):
        self.commit_locally()
        self.ran("pytest", code=1)
        reason = self.stop("Pushed, and all tests pass.")["reason"]
        self.assertIn("ahead of `origin/main`", reason)
        self.assertIn("exited 1", reason)
        self.assertEqual(reason.count("Principle P6"), 1)

    def test_no_message_is_silent(self):
        self.assertIsNone(self.stop(""))


class StopModes(HookCase):
    remote = True
    hooks_table = 'unsupported_claim = "advise"\ndirty_tree = "off"'

    def test_advise_mode_never_blocks_and_off_is_silent(self):
        self.write("src/app.py", "x = 1\n")
        self.git("commit", "-q", "-am", "local")
        out = self.stop("Pushed.")
        self.assertNotIn("decision", out)
        self.assertIn("ahead", out["systemMessage"])
        self.edited("src/app.py", "y = 2\n")
        self.assertNotIn("uncommitted", (self.stop("Done.") or {}).get("systemMessage", ""))


class StopWithoutGit(HookCase):
    def test_outside_a_git_repository_only_record_checks_run(self):
        import shutil

        shutil.rmtree(self.repo / ".git")
        self.assertIsNone(self.stop("Pushed and committed; working tree is clean."))
        self.ran("pytest", code=1)
        self.assertEqual(self.stop("All tests pass.")["decision"], "block")


if __name__ == "__main__":
    unittest.main()
