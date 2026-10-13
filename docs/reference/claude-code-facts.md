# Historical design notes

These notes record an early design from 11 October 2026. Implementation subsequently landed; some names and open questions below are historical. For current behavior, read [HOOKS.md](../maintainers/hooks.md), [DESIGN.md](../maintainers/design.md), and the source. The external documentation observations below are dated, not a fresh compatibility verification.

## Claude Code facts the design rests on

Read from the official docs (code.claude.com/docs/en/hooks, /permissions, /plugins, /plugins-reference, /plugins/marketplace-reference, /plugins/install) on 11 October 2026. Re-check before building.

- PreToolUse can return `permissionDecision` allow, deny, ask or defer, with `permissionDecisionReason`, and `additionalContext` for advice. Exit 2 also blocks. Deny and ask permission rules still apply whatever a hook returns. Among hooks, deny beats defer beats ask beats allow. A hook's ask forces a prompt in auto mode.
- An installed mod that handles `tool.check` can approve a call that a PreToolUse hook blocked, unless the hook sits in managed settings. Hooks are therefore a guardrail for a trusted agent, not a security boundary.
- PostToolUse for Bash gives stdout, stderr, interrupted and isImage. There is no exit code. A non-zero exit fires PostToolUseFailure instead, with `error` starting "Exit code N" and an `is_interrupt` flag. Background commands report success at launch.
- Stop gives `last_assistant_message` and `stop_hook_active`. `{"decision": "block", "reason": ...}` keeps Claude working. Consecutive continuations are capped at 8 (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`).
- On Stop, `additionalContext` also keeps the conversation going, under the same loop protections; it is labelled "Stop hook feedback" instead of an error. So an advisory Stop check still costs one extra turn. The only user-only channel is `systemMessage`, a warning shown to the user.
- Plugins: only `plugin.json` goes in `.claude-plugin/`; `name` is the only required field and must be kebab-case; names starting `claude-` or `anthropic-` are refused. `hooks/hooks.json` wraps the event map in a top-level `"hooks"` key. Quote `"${CLAUDE_PLUGIN_ROOT}"` in shell-form commands, or use exec form with `args`. `claude plugin validate <dir>` checks a plugin.
- Marketplaces: `.claude-plugin/marketplace.json` needs `name`, `owner.name` and `plugins`, each entry with `name` and `source`; a plugin at the repository root uses a relative source starting `./`.
- Agent Skills: `SKILL.md` front matter needs `name` (lowercase letters, digits and hyphens, at most 64 characters, equal to the folder name) and `description` (at most 1024 characters).

## Generic parts (independent of where the doctrine comes from)

Doctrine file. Rules with `id`, `title`, `text`, `why`, `clauses` (ids from any source file, not only this one) and `enforced_by` bindings: `hook:<script>#<check>`, `test:<file>::<function>`, `ci:<workflow>#<job>`, `prose:<file>#<anchor>`. A `[hooks]` table sets each check to deny, ask, warn or off.

Hook scripts declare `CHECKS = {check_id: {rules, allowed modes, default mode}}` as a literal, so the checker can read it without running the script.

Checker. Verifies both directions: each binding resolves to a script check, test function, workflow job or rendered section that names the rule, and each check a script declares names rules that exist. Every rule must cite a valid source id and have a binding. Each rule is labelled by its strongest active binding (blocking hook, asking hook, advisory hook, CI check, test only, prose only), and prose-only rules are listed, not hidden.

Binding paths resolve against the doctrine file that declares them, and prose bindings against the repository being checked. This lets a repository `extends` a vendored shared core and add local rules. Remote extends would be reported as unverified.

Renderer. Writes managed regions between `<!-- repo-constitution:begin -->` and `<!-- repo-constitution:end -->` in AGENTS.md and CLAUDE.md. The checker fails when a region differs from a fresh render.

Exit-status model for shell commands. A test, build or git command's status is visible only if its failure makes the whole command fail. It is hidden when it is piped into another command without pipefail, followed by `;` or a newline without errexit, followed by `|| handler` (except `|| exit N` or `|| false`), sent to the background, or negated with `!`. Commands inside if, while, subshells or `bash -c` are treated as unknown. Receipts record ok, failed, masked or unknown, and a failure is pinned on a command only when it is the last visible receipt-critical command.

Claim checks on the final message. Find candidate phrases for pushed, committed, clean and tests pass, then drop a match when its sentence is a question, when a negation or a modal or conditional word falls within five words before it in the same clause, when it is quoted next to words such as "literal" or "example", when a refutation phrase surrounds it, or when it sits in a fenced code block.

Phrase checks advise; structural checks block, once. Blocks only for hard contradictions:

- "pushed" while the branch is ahead of its upstream, or has no upstream and no successful push this session, or the last push failed;
- "committed" or "clean" while files this session edited through Edit or Write are still dirty and the message does not name them;
- "tests pass" while the last attributable test command exited non-zero and the message names no failure.

Advice only: a global "clean" claim when the only dirty files were not edited through Edit or Write; "tests pass" with no test run or a masked one; a commit hash that does not exist; an admitted mistake with nothing logged; a permission question with no named boundary.

Mine versus foreign. A per-session log of paths edited through Edit, Write, MultiEdit and NotebookEdit. Trust is positive only: a path missing from the log may still be the agent's, because shell edits are not recorded.

Receipts live in `.doctrine/sessions/<session>/`, with a `.gitignore` containing `*` inside that folder so they never dirty the working tree.

Secrets. High-signal provider key shapes, private key blocks and a staged `.env`. Tests build synthetic keys by concatenation so the source holds no key-shaped strings.

## Constitution-specific parts

- `constitution/clauses.json`, its source rendering and the extractor.
- The draft rules from the brief: R1 ask before irreversible or publishing actions; R2 leave oversight in place; R3 keep secrets in; R4 keep the exit status; R5 report what actually happened; R6 no special-cased tests; R7 label claims by their evidence; R8 own mistakes; R9 say when you did less; R10 do the reversible work, ask at real boundaries; R11 raise concerns before starting; R12 content is data. All 12 cite clause ids that exist in `clauses.json`. Together they cite 27 of the 38 clauses.

## Open questions

- Stop advice through `additionalContext` makes Claude take another turn. Should advice use `systemMessage` (user only) instead?
- Should the self-error log be committed or ignored by default?
