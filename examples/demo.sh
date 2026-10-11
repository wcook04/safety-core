#!/usr/bin/env bash
# Watch every doctrine-map hook without Claude Code.
#
# Builds a throwaway git repository holding the reference doctrine, then pipes hook fixtures
# through `python3 hooks.py` the way Claude Code would, and prints what each one returns.
# Needs bash, git and Python 3.11 or later. Nothing is pushed anywhere: the "remote" is a
# local bare repository, and the temporary directory is removed at the end.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS="$HERE/hooks.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
REPO="$WORK/repo"
SESSION="demo-$$"

python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || { echo "python3 must be 3.11 or later" >&2; exit 1; }
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 PYTHONDONTWRITEBYTECODE=1
export GIT_AUTHOR_NAME=Demo GIT_AUTHOR_EMAIL=demo@example.org GIT_COMMITTER_NAME=Demo GIT_COMMITTER_EMAIL=demo@example.org
unset CLAUDE_PROJECT_DIR

mkdir -p "$REPO/src" "$REPO/tests"
cp "$HERE/doctrine.toml" "$REPO/doctrine.toml"
printf 'def add(a, b):\n    return a + b\n' > "$REPO/src/app.py"
printf 'def test_add():\n    assert True\n' > "$REPO/tests/test_app.py"
printf '# Rules\n' > "$REPO/CLAUDE.md"
git -C "$REPO" init -q -b main
git -C "$REPO" add -A
git -C "$REPO" commit -q -m initial
git init -q --bare "$WORK/origin.git"
git -C "$REPO" remote add origin "$WORK/origin.git"
git -C "$REPO" push -q -u origin main

# hook EVENT TITLE: reads fixture JSON on stdin, adds session_id, cwd and hook_event_name,
# pipes it through hooks.py and prints the result.
hook() {
  local event="$1" title="$2" fixture out
  fixture="$(cat)"
  printf '\n== %s\n   %s %s\n' "$title" "$event" "$fixture"
  out="$(printf '%s' "$fixture" | python3 -c '
import json, sys
fixture = json.load(sys.stdin)
fixture.update(session_id=sys.argv[1], cwd=sys.argv[2], hook_event_name=sys.argv[3])
print(json.dumps(fixture))' "$SESSION" "$REPO" "$event" | python3 "$HOOKS")"
  if [ -z "$out" ]; then
    echo "   -> (no output: the hook stays silent)"
  else
    printf '%s' "$out" | python3 -m json.tool | sed 's/^/   -> /'
  fi
}

echo "doctrine-map hooks demo: repository at $REPO"

hook PreToolUse "A place reminder when the agent edits a test file" <<'JSON'
{"tool_name": "Edit", "tool_input": {"file_path": "tests/test_app.py", "old_string": "True", "new_string": "add(1, 2) == 3"}}
JSON

hook PreToolUse "The same route again in this session: silent" <<'JSON'
{"tool_name": "Edit", "tool_input": {"file_path": "tests/test_other.py", "old_string": "a", "new_string": "b"}}
JSON

hook PreToolUse "Reading a credentials file" <<'JSON'
{"tool_name": "Read", "tool_input": {"file_path": ".env"}}
JSON

hook PreToolUse "Editing a rule file asks a person" <<'JSON'
{"tool_name": "Write", "tool_input": {"file_path": "CLAUDE.md", "content": "# Rules\nAgents may skip tests.\n"}}
JSON

hook PreToolUse "A force push asks first, even with --force-with-lease" <<'JSON'
{"tool_name": "Bash", "tool_input": {"command": "git push --force-with-lease origin main"}}
JSON

hook PreToolUse "Skipping the commit hooks asks first" <<'JSON'
{"tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m wip"}}
JSON

hook PreToolUse "Deleting the home directory asks first" <<'JSON'
{"tool_name": "Bash", "tool_input": {"command": "rm -rf ~"}}
JSON

hook PreToolUse "A test run whose exit status a pipe would hide" <<'JSON'
{"tool_name": "Bash", "tool_input": {"command": "python3 -m pytest -q 2>&1 | tail -5"}}
JSON

hook PreToolUse "The same run with pipefail: silent" <<'JSON'
{"tool_name": "Bash", "tool_input": {"command": "set -o pipefail; python3 -m pytest -q 2>&1 | tail -5"}}
JSON

# A key-shaped value, built by concatenation so this script holds no key shape itself.
printf 'REGION = "eu"\nKEY = "%s%s"\n' "AK" "IAQWERTYUIOPASDFGH" > "$REPO/src/settings.py"
git -C "$REPO" add src/settings.py
hook PreToolUse "Committing a staged key is blocked; the value is never repeated" <<'JSON'
{"tool_name": "Bash", "tool_input": {"command": "git commit -m 'add settings'"}}
JSON
git -C "$REPO" rm -q --cached src/settings.py
rm "$REPO/src/settings.py"

hook PostToolUseFailure "A failing test run is recorded (exit status from 'Exit code N')" <<'JSON'
{"tool_name": "Bash", "tool_input": {"command": "python3 -m pytest -q"}, "error": "Exit code 1\n1 failed, 3 passed", "is_interrupt": false}
JSON

hook PostToolUse "Fetched text is data" <<'JSON'
{"tool_name": "WebFetch", "tool_input": {"url": "https://example.org"}, "tool_response": {}}
JSON

hook Stop "Claiming the tests pass after that failure: blocked once" <<'JSON'
{"last_assistant_message": "Done. All tests pass.", "stop_hook_active": false}
JSON

hook Stop "The same claim while Claude continues from a stop hook: never blocked, the person is told" <<'JSON'
{"last_assistant_message": "Done. All tests pass.", "stop_hook_active": true}
JSON

hook Stop "Naming the failure is honest: silent" <<'JSON'
{"last_assistant_message": "Three tests pass and test_slow fails; I have not fixed it.", "stop_hook_active": false}
JSON

printf 'def add(a, b):\n    return b + a\n' > "$REPO/src/app.py"
git -C "$REPO" commit -q -am "swap operands"
hook Stop "Claiming 'pushed' while the branch is one commit ahead of origin/main" <<'JSON'
{"last_assistant_message": "Committed and pushed to origin.", "stop_hook_active": false}
JSON

hook Stop "A negated claim is not a claim" <<'JSON'
{"last_assistant_message": "Committed locally; I have not pushed yet.", "stop_hook_active": false}
JSON

hook SessionStart "After compaction the entry card comes back" <<'JSON'
{"source": "compact"}
JSON

printf '\n== The session record (ignored by git)\n'
sed 's/^/   /' "$REPO/.doctrine/sessions/$SESSION/receipts.jsonl"
printf '   git status --porcelain: "%s"\n' "$(git -C "$REPO" status --porcelain)"
