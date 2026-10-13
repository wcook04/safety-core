# Design

## The problem

AI agents now do real work in repositories: they edit code, run migrations, push
branches and publish packages. Teams write rules for them in AGENTS.md, CLAUDE.md and
editor rule files. Three things go wrong.

1. **Rules are not delivered when they matter.** A long root file is skimmed or lost, and
   rules relevant to one directory sit beside rules for every other. Agents follow short,
   always-present guidance better than guidance they must think to look up, and
   module-level files beat one large root file.
2. **Rules are not enforced.** A rules file is context, not configuration. Instructions
   alone do not reliably stop bad actions; hooks and checks can intervene in the
   specific cases they recognise. Without inspecting the configuration, people cannot
   say which of their rules are enforced and which are only hoped for.
3. **Rules drift.** Several copies (one per tool, one per directory) fall out of step, and
   an agent can edit the rules it works under.

## The idea

Write the doctrine once, in one file. Link each rule to the places in the repository it
governs and to what enforces it. Compile those local links into everything else:

- **Entry:** a compressed doctrine every agent reads on arrival, inside a line budget.
- **Place:** the principles for a directory reach the agent when it works there, through
  path-scoped rules and hook reminders.
- **Enforcement:** the rules that must hold are hooks and checks, not sentences.
- **Map:** one picture of the doctrine and the repository that shows which rules are
  enforced, which are only words, and which places no rule covers.

Coherence comes from local links that can be compiled and checked.

## The shape

The small command and hook core stays at the root. The viewer and guides have separate owners:

| File | Role |
|---|---|
| `doctrine.toml` | the reference doctrine |
| `doctrine.py` | the tool, standard library only: init, build, check, explain, map, log-error |
| `hooks.py` | the Claude Code hooks; its `CHECKS` and `WIRING` are literals that `doctrine.py` reads with `ast` |
| `viewer/map.html` | the viewer, one self-contained file |
| `docs/guides/agent-setup.md` | what an agent does to adopt a doctrine, and what it reports |

`init` copies the doctrine, `safety.py`, `doctrine.py`, `hooks.py` and the viewer into the target's
`.doctrine/` folder and wires the hooks into `.claude/settings.json`. Nothing is
installed. Local state (session records, the built graph, the mistakes log) stays in
`.doctrine/` and is ignored by git.

## The model

| Thing | What it is | Count |
|---|---|---|
| Axiom | A root commitment, with a dense clause and the anti-axiom it rejects | at most 7 |
| Principle | A working rule that serves one or more axioms, paired with its anti-principle | about 15 |
| Route | Paths in the repository, the principles they receive, and a factual reminder | as needed |
| Enforcer | A hook, check or command that makes a principle hold | as built |
| Source | A published text the claim rests on | as cited |

Each principle declares an enforcement level: `block`, `ask`, `check`, `remind`,
`advise` or `prose`. The build computes the level actually present by resolving the
enforcers. The map and the check report the difference.

Every principle has an anti-principle because over-applying a rule is its own failure:
"ask before irreversible actions" is paired with "do reversible work without ceremony".

## Compile targets

| Output | Read by | Holds |
|---|---|---|
| managed region in `AGENTS.md` | Codex, Gemini CLI, Cursor, Copilot and other AGENTS.md readers | the entry card and a table of where rules live |
| managed region in `CLAUDE.md` | Claude Code | `@AGENTS.md` and one pointer line |
| `.claude/rules/doctrine-<route>.md` | Claude Code, on files that match `paths:` | the route's reminder and its principles' one and three lines |
| `.rulesync/rules/doctrine-<route>.md` (`build --export rulesync`) | rulesync, which writes about sixty agents' own formats | the same, with `targets` and `globs` |

Route patterns use .gitignore-style meaning: a pattern without a slash matches at any
depth, and a match covers everything beneath it. The build exports them as plain globs
with the same meaning. Generated files carry a header naming doctrine.toml as their
source, and `check` fails when any of them differs from a fresh build. Text outside the
managed regions is never changed.

## Enforcers and coverage

`check` resolves each reference in a principle's `enforced_by`:

| Reference | Present when | Level |
|---|---|---|
| `hook:<event>#<key>`, `stop:<name>#<key>` | `hooks.py` has the check in `CHECKS`, and repository settings wire its event and required tool matchers | its configured mode, limited by the event's capabilities; disabled or uncovered checks receive no credit |
| `route:<id>` | the route exists and matches at least one file | remind |
| `check:links`, `check:drift` | always: `doctrine.py check` implements them | check |
| `cli:log-error` | always | prose: it records a lesson and stops nothing |
| `guard:<tool>` | `.claude/settings.json` runs that tool as a hook | the principle's declared level |

External guards are credited without being named. When `.claude/settings.json` runs nah
or cc-safety-net, they count for the `irreversible` (ask) and `secrets` (block) checks;
destructive_command_guard counts for `irreversible` only, because its secret packs are
opt-in. Cupcake enforces only the policies written for it, so it counts only where a
principle names `guard:cupcake`. Each credit names the tool with `by`.

A principle's effective level is the strongest present enforcer, and at least `remind`
when a live route carries it, because the route's rule file reaches the agent there.
`check` then reads each principle at each top-level place as enforced (a hook or check
stops or fails it), reminded (text reaches the agent there) or words (the entry card
only), prints that table, and ends with "N of M principles enforced beyond words".

It fails on an enforcer that does not exist, a principle that declares a level with
nothing behind it, a stale generated file, and an entry card over its budget. It warns on
dead routes, on sensitive places no route reaches, on hook checks that do not list the
principle naming them, and when hooks.py is not wired.

## Hooks (Claude Code first)

- **PreToolUse.** On Edit, Write and Bash, find the routes for the paths involved and add
  their reminders as factual context, once per session per route. Ask before irreversible
  or publishing commands, before edits to the rule files, and before commands that bypass
  checks. Block commits whose staged changes contain key-shaped secrets. Remind when a
  test, build or git command's exit status would be hidden.
- **PostToolUse and PostToolUseFailure.** Record what ran and how it exited, and which
  files were edited, under `.doctrine/sessions/` (ignored by git). After web fetches, note
  that fetched text is data.
- **Stop.** Compare the final message's claims (tests pass, committed, pushed, clean) with
  the session record and git. Block once on a hard contradiction. Everything softer is a
  note to the person, never another agent turn.
- **SessionStart (after compaction).** Re-inject the entry card.

Phrase checks advise; structural checks block. Hooks are a guardrail for a trusted but
fallible agent. They are not a sandbox or a security boundary, and an agent with enough
access can route around them. Pair them with sandboxing for anything that matters.

## Commands

| Command | Does |
|---|---|
| `python3 doctrine.py init` | adopts the reference doctrine in `.doctrine/`, keeping only routes that match this repository, wires the hooks, builds |
| `python3 doctrine.py build` | writes every projection and `.doctrine/graph.json` |
| `python3 doctrine.py check` | fails on missing enforcers, drift and an over-budget entry card; warns on dead routes and unrouted sensitive places; prints coverage |
| `python3 doctrine.py explain <path>` | shows exactly what an agent receives at a path |
| `python3 doctrine.py map` | writes a self-contained `doctrine-map.html`; `--serve` runs a local map that rebuilds as you edit |
| `python3 doctrine.py log-error` | records a mistake and its lesson in `.doctrine/mistakes.jsonl` |

## The map

The map is the doctrine and the repository in one picture, read left to right: axioms,
principles with their anti-principles, routes, and the repository's places. A line into a
place means an agent working there receives the principle. Each principle's gauge shows
its effective level, empty when it is only words. Gaps show where they are: sensitive
places no rule covers, routes that match nothing, enforcers that do not exist.
[MAP.md](../guides/map.md) describes it in full.

Two questions the map answers in a click:

- **What does an agent receive here?** Pick a place to see the entry card plus the
  reminders and checks that apply there.
- **What actually holds?** Hide everything that is only words to see the doctrine as
  the repository enforces it.

Run it locally with `python3 doctrine.py map --serve`; it rebuilds and redraws as you
edit doctrine.toml or move files.

## What it is not

Not a sandbox, not a policy engine for production systems and not a replacement for code
review. It makes a repository's rules for agents explicit, delivered, checked and
visible, so the gap between the rules you wrote and the rules that hold is something you
can see and close.

## Coverage boundary

Only `block`, `ask` and `check` count as enforced. Reminders and advice remain visible
but do not enter that total. Hook credit requires repository event wiring and respects
mode overrides; it is a configuration report, not proof of execution in an agent host.
