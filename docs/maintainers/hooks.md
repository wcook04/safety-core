# Hooks

`hooks.py` is one standard-library Python file. Its ordinary mode runs on five
Claude Code events and delivers the doctrine where the agent works, keeps a record of what actually ran, and
compares the agent's final message with that record. In a repository with no doctrine
(`doctrine.toml` or `.doctrine/doctrine.toml` in the working directory or above it) it does
nothing. The separate opt-in [push-policy handler](#optional-project-specific-push-policy)
needs no doctrine and has stricter error behavior.

## Install

- **Per repository.** `python3 doctrine.py init` copies `hooks.py` and `doctrine.py` into
  `.doctrine/` and adds one entry per event to `.claude/settings.json`, each running
  `python3 "$CLAUDE_PROJECT_DIR"/.doctrine/hooks.py`.
- **As a plugin.** `hooks/hooks.json` runs `python3 "${CLAUDE_PLUGIN_ROOT}/hooks.py"` on the
  same events. Use one or the other: Claude Code runs a plugin's hooks and a settings file's
  hooks separately, so wiring both runs every check twice.

Requirements: `python3` on the `PATH` must be Python 3.11 or later, and `git` for the commit
and claim checks. On an older `python3` the hooks do nothing and say so once, when a session
starts.

| Event | Matcher | Timeout |
|---|---|---|
| SessionStart | `startup\|clear\|compact` | 10 s |
| PreToolUse | `Bash\|Edit\|Write\|MultiEdit\|NotebookEdit\|Read` | 15 s |
| PostToolUse | `*` | 10 s |
| PostToolUseFailure | `Bash` | 10 s |
| Stop | (all) | 30 s |

The table is the literal `WIRING` in `hooks.py`; `doctrine.py init` and `hooks/hooks.json`
both follow it.

The final command-claim check needs Bash receipts from both `PostToolUse` and
`PostToolUseFailure`. `check` warns if either event is missing or receipt recording
is off. A wired Stop hook can still check contradictions against Git's current
state, so that narrower support remains credited.

## Checks

Each check has a default level. Messages name the principle the doctrine attaches to the
check: a principle whose `enforced_by` names it (any reference ending in `#<check>`, such as
`hook:pre_tool#irreversible`), or else the principle listed for the check in `CHECKS`.

| Check | Event | Default | Principle in the reference doctrine | What it does |
|---|---|---|---|---|
| `reminders` | PreToolUse | remind | each route's own | When the agent reads, edits or runs a command in a place a route covers, adds that route's reminder and the one-line text of its principles. Once per route per session, and again after compaction. |
| `rule_files` | PreToolUse | ask | P15 | Asks before an Edit or Write to a rule file, and before a shell command writes one (a redirection, `tee`, `sed -i`, `cp` or `mv` onto it, or `rm`). Rule files are the paths of the `agent-rules` route (or `AGENTS.md`, `CLAUDE.md`, `.claude/**` and `.cursor/**` when there is no such route), plus the doctrine itself and everything in `.doctrine/`. `doctrine.py build` writes them without asking, because it writes through Python rather than a shell redirection. |
| `masked_status` | PreToolUse | remind | P5 | Notes when a test, build or git command's exit status would not reach the shell (see the exit-status model below). The first note in a session explains how to keep the status; later ones are one line. |
| `irreversible` | PreToolUse | ask | P2 | Asks before the commands in "The built-in guard" below, naming what each will do. |
| `bypass_checks` | PreToolUse | ask | P1 | Asks before a command that skips or switches off the hooks that run on commit, push and merge: `--no-verify` on `git commit`, `push` or `merge`, `git commit -n` (read the way git reads short options, so `-m -n` is a message), `HUSKY=0`, `SKIP=` alongside a commit or a pre-commit run, setting or unsetting `core.hooksPath` (including `git -c core.hooksPath=...`), and `pre-commit uninstall`. Mentions such as `grep -- --no-verify` or a commit message containing the words are left alone. |
| `secrets` | PreToolUse | block | P11 | Blocks a `git commit` whose changes hold a key-shaped value or a `.env` file, naming the file and line but never the value. Asks before an Edit or Write whose new content holds a key shape, unless git ignores the file. |
| `secret_reads` | PreToolUse | off | P11 | Optional check on every Read matched by the configured `secrets` route's read paths. Set to `ask` for approval or `block` to deny. Does not inspect contents or share reminder deduplication. |
| `receipts` | PostToolUse | remind | P6 | Records every shell command and how it exited. The first time a test, build, commit or push fails in a session, notes that the end-of-turn check will compare claims with this record. |
| `edit_ledger` | PostToolUse | record | P6 | Records each path changed through Edit, Write, MultiEdit or NotebookEdit. |
| `untrusted_content` | PostToolUse | remind | P12 | After WebFetch, WebSearch or any tool whose name contains "fetch" or "browse", notes once per tool per session that the fetched text did not come from the person. |
| `unsupported_claim` | Stop | block | P6 | Compares the final message's claims with the record and git (see "The claim check"). Blocks once on a hard contradiction; softer findings go to the person. |
| `permission_gate` | Stop | advise | P3 | Tells the person when the final message asks to go on ("should I proceed?") without naming an irreversible step, a cost or an open question. |
| `dirty_tree` | Stop | advise | P4 | Tells the person when files edited during the turn have uncommitted changes the final message does not mention. |
| `unlogged_mistake` | Stop | advise | P9 | Tells the person when the final message admits a mistake and nothing was recorded with `doctrine.py log-error` during the session. |
| `entry_card` | SessionStart | remind | all of them | After compaction, delivers the doctrine's entry card again. |

`CHECKS` is a literal at the top of `hooks.py`, so `doctrine.py check` reads it without
running the file.

Checks whose reported level depends on particular tools also declare those tools in
`CHECKS`. Configuration coverage requires the matching event's Safety Core hook groups
to cover all of them. For example, a `PreToolUse` hook restricted to `Read` cannot earn
approval or blocking credit for a Bash command guard. Matching is case-sensitive;
unrelated hooks do not provide coverage. This verifies recognized configuration, not
whether the host actually ran a hook or every possible command is detected.

## Changing a level

Add a `[hooks]` table to the doctrine:

```toml
[hooks]
irreversible = "block"     # deny instead of asking
masked_status = "advise"   # tell the person instead of the agent
dirty_tree = "off"
entry_on_startup = true    # also deliver the entry card when a session starts
```

| Mode | PreToolUse | PostToolUse | Stop | SessionStart |
|---|---|---|---|---|
| `block` | denies the call; the reason goes to Claude | a note to Claude (the tool has already run) | keeps Claude working once, with the reason | a note to Claude |
| `ask` | a permission prompt showing the reason to the person | a note to Claude | a warning to the person | a note to Claude |
| `remind` | a note to Claude | a note to Claude | a warning to the person | a note to Claude |
| `advise` | a warning to the person | a warning to the person | a warning to the person | a warning to the person |
| `record` | nothing said | nothing said; the record is kept | nothing said | nothing said |
| `off` | the check does not run | the check does not run, and nothing is recorded | the check does not run | the check does not run |

### Approval for each secret-path read

To ask before every matching Claude Code Read call, add this to your doctrine:

```toml
[hooks]
secret_reads = "ask"
```

This check is off by default and uses the `secrets` route with `on = ["read", ...]`.
Edit that route's `paths` to match your project. If adoption dropped the route
because no secret paths existed, restore it from the reference doctrine first.
The reference route also includes
`.env.example` through `.env.*`; narrow it if those examples should be readable
without approval. The check runs for repeated reads even when the reminder has
already appeared, and works with `reminders = "off"`. It never reads the file's
contents itself.

The boundary is the configured route inside the repository and the `Read` tool;
shell commands, other tools, paths outside the repository and unconfigured paths
are not covered. A `PreToolUse` matcher must include `Read`, and the host must
actually run the hook. Setting all reminders to `ask` still asks only once per
route per session and is not a substitute for this check. To include its
configuration in the coverage map, add `hook:pre_tool#secret_reads` to the relevant
principle's `enforced_by`, retaining any existing commit-scan reference.

Recursive-delete reasons name the resolved target. If a sandbox sets its home to
`/`, deleting `~` is described as the filesystem root and also the resolved home
directory. An ordinary home still receives the home-directory reason.

On Stop, a note to Claude would cost an extra turn, so every mode but `block` becomes a
warning to the person. Key shapes in Edit or Write content are asked about at most, never
blocked, because the value has not reached a commit. A value outside these modes is ignored
and the default applies.

Notes to Claude are written as factual statements, because Claude Code's documentation warns
that text framed as instructions can be treated as a prompt injection.

## Optional project-specific push policy

The ordinary hook settings above retain their defaults. For projects that need
stricter Git push rules, `hooks.py --push-policy /absolute/path/push-policy.json`
is a separate, opt-in `PreToolUse` handler. It reads no doctrine and does not
run the event's command. Keep the ordinary hook installed too: the push handler
does not run secret scanning, rule-file checks or session recording.

A project-owned policy selects protected **full destination refs**, an `ask` or
`deny` decision, and whether to reject force pushes:

```json
{
  "version": 1,
  "protected_refs": ["refs/heads/main", "refs/heads/dev"],
  "decision": "deny",
  "deny_force": true,
  "deny_output": "exit2"
}
```

The optional `deny_output` is `"json"` by default or `"exit2"` for a denial
protocol based on status 2 and stderr. `decision: "ask"` requires JSON output;
combining it with `"exit2"` is rejected. The example chooses strict exit-code
denials. Use literal refs, not shell expressions or glob patterns. Different projects can
protect different branches or tags without changing the runtime. The same
validator is available without installing anything:

```sh
python3 .doctrine/hooks.py --check-push-policy /absolute/path/push-policy.json
```

Append a separate group to your existing `.claude/settings.json` under
`hooks.PreToolUse`; do not replace existing groups:

```json
{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.doctrine/hooks.py --push-policy \"$CLAUDE_PROJECT_DIR\"/.doctrine/push-policy.json",
    "timeout": 15,
    "onFailure": "block"
  }]
}
```

Review the policy and settings, start a new Claude Code session and inspect the
host's hook configuration. The current Claude Code hook reference documents
`onFailure: "block"` for startup errors and timeouts; verify your installed host
supports that field. These protocol tests do not establish that host behavior.
This is a deliberate manual addition; `init` does
not create this policy or enable it, and rebuilding does not install it. It
receives **no automatic enforcement credit in the current doctrine map**.
`--check-push-policy` validates the policy, not wiring or live host execution.

The handler inspects a limited explicit Git push grammar. It judges the remote
**destination**, so `HEAD:main`, `refs/heads/main` and deletion refspecs cannot
avoid a configured `refs/heads/main` restriction. An ordinary push with an explicit `source:full-destination` and
`--no-follow-tags` to an unprotected destination is neutral under this handler; other guards and
host permissions still apply. It never emits an `allow` decision.

A bare push, a source-only refspec, a dynamic or ambiguous destination, an
unsupported push option, a push without `--no-follow-tags`, or
wrapped/compound Git-looking command receives the configured decision rather
than being inferred safe. A source-only refspec may inherit a different
destination from `remote.<name>.push`; `--no-follow-tags` prevents ambient
`push.followTags` from adding destinations omitted from the command. This conservative rule can also flag harmless wrappers,
compound status commands or text quoting a Git command; review that tradeoff
before enabling it. The parser does not expand Git aliases, shell functions or
variables, inspect scripts, resolve remote configuration, or understand
PowerShell. Indirect calls such as a Python program that performs a push, recursive
submodule pushes, and actions inside Git hooks or on the server are outside
this direct-target command-line check. Use server-side branch protection and restricted
credentials for boundaries that must survive indirect execution or local edits.

Recognized policy decisions use exit 0 with Claude Code's `permissionDecision`
JSON (`ask` or `deny`), except a configured `deny_output: "exit2"` denial uses
status 2 and stderr with empty stdout. Missing/malformed policy, invalid event input and internal
handler errors exit 2 with a reason on stderr, regardless of the configured
`ask` mode. The explicit flag preserves that error behavior when policy parsing
fails; the ordinary handler's error behavior remains unchanged. This process cannot repair a missing Python runtime, an unstarted hook,
a host timeout or removed wiring. The host must apply its configured failure
behavior; removed wiring supplies no guard. Verify those cases at that host. See the
[host output contract](https://code.claude.com/docs/en/hooks#exit-code-output).

Before using this on real work, feed synthetic events for a protected destination,
a wrapped push, an ordinary status command and an explicit unprotected push such as
`git push --no-follow-tags origin HEAD:refs/heads/feature/review`.
Repeat with a missing/invalid policy and require exit 2. Do not execute the push
commands. A protocol result alone is not live host enforcement or full project
policy acceptance.

## The session record

Everything the hooks record lives in `.doctrine/sessions/<session id>/`:

- `receipts.jsonl`: one line per shell command, with the time, the event, the class (`test`,
  `build`, `git-commit`, `git-push` or `other`), the exit status, whether it ran in the
  background, the command with key shapes replaced by `[redacted]`, and the status of each
  test, build or git command in it: `ok`, `failed`, `masked` or `unknown`.
- `edits.jsonl`: one line per path changed through Edit, Write, MultiEdit or NotebookEdit.
- `once/`: markers for notes delivered once per session, created atomically so parallel
  tool calls cannot deliver the same note twice.
- `started` and `last_stop`: when the record began and when the last turn ended, used to
  spot a mistake logged during the session and to tell this turn's edits from earlier ones.

A `.gitignore` holding `*` keeps the record out of git. Records older than 14 days are
removed when a session starts.

Exit statuses come from Claude Code. PostToolUse fires only when a command succeeds, so it
records exit 0. PostToolUseFailure carries `Exit code N` as the first line of its error,
and the hook reads N from it. An interrupted command, an error without that line and a
background command (which reports success when it starts) are recorded as unknown.

## The exit-status model

A test, build or git command's status reaches the shell only if its failure makes the whole
command fail. It is hidden when the command is:

- piped into another command without `pipefail` (`pytest | tail -5`);
- followed by `|| handler`, except `|| exit N` and `|| false` (`pytest || true`);
- followed by `;` or a new line without `set -e` (`pytest; echo done`);
- sent to the background with `&`, or negated with `!`.

`set -o pipefail` (or zsh's `setopt pipefail`), reading `PIPESTATUS` or `pipestatus`,
`set -e` and `&&` keep it. A status that is only printed (`pytest; echo $?`) is visible in
the output, so no note is added, but the record calls it unknown because the shell's own
exit code is then `echo`'s. Commands inside `if`, `while`, `for`, `case`, braces, subshells
and `bash -c` count as unknown. A failure is pinned on a command only when it is the last
one the exit status can come from: when `pytest && git push` fails, the push did not
succeed, and whether the tests passed is unknown.

Recognised commands: `pytest`, `python -m pytest` or `unittest`, `tox`, `nox`, `npm`,
`pnpm`, `yarn` and `bun` test and build scripts, `jest`, `vitest` and `mocha` (directly or
through `npx`), `cargo`, `go`, `dotnet`, `swift` and `deno` test and build, `make`,
`gradle`, `mvn`, `rspec`, `phpunit`, scripts whose name contains "test", and `git commit`,
`push`, `merge`, `rebase` and `pull`. Wrappers such as `sudo`, `env`, `timeout`, `uv run`,
`poetry run` and `bundle exec` are looked through.

## The claim check

The Stop hook finds four kinds of claim in the final message: pushed, committed, clean and
tests pass. A phrase does not count as a claim when:

- its sentence is a question;
- a negation, condition or instruction ("not", "if", "once", "make sure") or reported speech
  ("said") falls within five words before it in the same clause, or a modal verb ("would",
  "should", "can") within three;
- its subject is someone else ("you pushed", "they committed");
- a status such as "no", "pending" or "0" follows it (`Pushed: no`);
- the sentence places it in the past ("before this change", "previously");
- it is quoted beside words such as "example", "phrase" or "word", or a refutation surrounds
  it ("do not say", "would be false");
- it sits in a fenced code block, a block quote, an unticked checkbox, a URL or a path.

Hard contradictions block once:

- **pushed**: the last push in the session failed; or no remote-tracking branch holds HEAD
  and either the branch is ahead of its upstream, or it has no upstream and the record holds
  no successful push; or the repository has no remote.
- **committed** or **clean**: files edited during the session through Edit or Write still
  have uncommitted changes, and the message does not name them.
- **tests pass**: the last test command in the session failed, and the message names no
  failure.

Each contradiction blocks at most once per session, and never when `stop_hook_active` is
true (Claude is already continuing because of a stop hook). After that the person sees it as
a warning instead. Softer findings are always warnings to the person: a "clean" claim when
the only changes are ones the session did not make through Edit or Write, "tests pass" with
no recorded test run or with a hidden exit status, and a named commit hash that does not
exist.

Mine versus foreign: the edit ledger records only paths changed through Edit, Write,
MultiEdit and NotebookEdit. A path missing from it may still be the agent's, because shell
edits are not recorded, so changes outside the ledger lead to a warning, never a block.

The claim check is a self-contained section of `hooks.py` (`find_claims`, `judge` and the
helpers between them), so it can be used or tested on its own.

## The built-in guard

The irreversible check is a floor, not full coverage. It asks before:

- force pushes, including `--force-with-lease`, `--mirror` and `+refspec`, and pushes that
  delete remote branches or tags;
- `git reset --hard`, `git branch -D`, and `git clean` with `-f`;
- recursive `rm` of the filesystem root, the home directory, the repository root (or
  everything in it, or its `.git`), or any path outside the project except below the
  system's temporary directories;
- `terraform destroy` and `terraform apply -destroy` (and the same through `tofu`);
- package publishing: `npm`, `pnpm`, `yarn` and `bun publish`, `twine upload`,
  `cargo publish`, `poetry publish`, `uv publish`, `flit publish` and `gem push`, unless run
  as a dry run;
- `gh repo create --public` and `gh repo edit --visibility public`.

For publishing, the dry-run exemption recognizes an enabled `--dry-run` on
`npm`, `pnpm`, `yarn`, `bun`, `cargo`, `poetry` and `uv`. Explicit false values,
`--no-dry-run` (including `=true`), and flags after `--` do not enable it. `-n` is not a publishing
dry run: [npm uses it for `--no-yes`](https://docs.npmjs.com/cli/v11/using-npm/config/)
and [Poetry for `--no-interaction`](https://python-poetry.org/docs/cli/).
Twine, flit and `gem push` receive no dry-run exemption. This is selected option
recognition, not a complete parser for every publisher or version.

It also reads the body of `bash -c '...'` and `eval '...'`. For fuller coverage, add a
semantic shell guard such as nah, cc-safety-net or destructive_command_guard alongside these
hooks; `doctrine.py check` credits them when `.claude/settings.json` runs them.

The commit scan reads the staged diff. When the commit uses `-a`, or the same command runs
`git add` first, it also reads unstaged changes to tracked files, and with `git add` the new
files it would pick up. Key shapes: AWS access keys, GitHub, GitLab, Slack, npm and PyPI
tokens, Anthropic, OpenAI and Google API keys, Stripe live keys and private key blocks. A
staged `.env` or `.env.*` file is blocked too, except `.env.example`, `.env.sample`,
`.env.template` and `.env.dist`. Generic `password=` values are not checked, because they
produce too many false alarms.

## Limits

- **A guardrail, not a security boundary.** The hooks are for a trusted but fallible agent.
  An agent with shell access can route around them: write a script and run it, edit a file
  through Python, or build a command from variables. An installed mod that handles
  `tool.check` can approve a call a hook blocked, unless the hook sits in managed settings.
  Pair the hooks with sandboxing and narrowly scoped credentials for anything that matters.
- **Shell text is read, not run.** Variables, aliases, functions and the inside of `$(...)`
  are not followed, and a target such as `rm -rf "$DIR"` is not judged.
- **Claims are English phrases.** The claim check misses claims worded in other ways and can
  misread unusual wording. That is why it blocks only on hard contradictions, and only once.
- **A subagent's final message is not checked.** The hooks are not wired to SubagentStop.
  A subagent's tool calls still pass through the PreToolUse and PostToolUse hooks.
- **Failures fail open.** A hook that times out does not block (Claude Code's rule), and an
  internal error writes one line to stderr and exits 0.
- **Platforms.** Tested on macOS. The hooks use only Python and git, so Linux should behave
  the same, but it has not been run there; Windows is untested.

## Watch it run

`bash examples/demo.sh` builds a throwaway repository, pipes a fixture for each check
through `python3 hooks.py`, and prints what comes back. It needs bash, git and Python 3.11
or later, pushes nothing anywhere and removes its temporary directory at the end.

The tests: `python3 -m unittest discover -s tests -p "test_hooks_*.py" -v`.
