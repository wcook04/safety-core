# Adopt and customize Safety Core

This walkthrough is for someone shaping their own coding-agent environment.
The useful unit is a project-owned rulebook with inspectable mechanisms.

## 1. Adopt it in a project

Clone Safety Core alongside your project, then run from your project:

```sh
python3 ../safety-core/safety.py init --target .
python3 .doctrine/safety.py check
git diff
```

Inspect untracked setup files too: Git's ordinary diff does not show their content.
Setup preserves existing instructions outside generated regions and merges hook
settings. It refuses to replace an existing doctrine by default. After adoption,
use the project-local `.doctrine/safety.py`.

Start a new session of your installed agent in this project so it can discover the
instructions and current settings. The generator does not itself launch a model.
Claude Code has runtime integration; other AGENTS.md readers receive instructions.
Check your host's own hook/settings view before relying on runtime behavior.

## 2. Give it an ordinary task

For example: "Fix the parser's handling of an empty input and run the relevant tests."
The intended experience is useful work without a request for approval at every
read, edit or test. Host permissions may still require approvals independently.

The root entry card supplies the broad rules. Path rules and hook reminders add
local context, such as preserving meaningful tests. A reminder is context the
model can follow, not a program that proves the edit respects the rule.

## 3. Change one rule and see the consequence

In `.doctrine/doctrine.toml`, add this table or update its existing key:

```toml
[hooks]
irreversible = "block"
```

Then run:

```sh
python3 .doctrine/safety.py build
python3 .doctrine/safety.py check
python3 .doctrine/safety.py map --serve --open
```

The implemented `irreversible` hook now denies recognized commands instead of
asking. Inspect P2 in the map: its effective mechanism changes. Returning the key
to `"ask"` restores the default prompt behavior. This setting applies to the
whole built-in check, not one package, environment or user intent.

Do not test this by actually publishing a package. A synthetic protocol event
lets you see the response without executing its `command` field. From the project:

```sh
python3 - <<'PY'
import json, pathlib, subprocess, sys
root = pathlib.Path.cwd()
event = {
    "hook_event_name": "PreToolUse",
    "session_id": "manual-synthetic-check",
    "cwd": str(root),
    "tool_name": "Bash",
    "tool_input": {"command": "npm publish"},
}
subprocess.run([sys.executable, str(root / ".doctrine/hooks.py")],
               input=json.dumps(event), text=True, check=True)
PY
```

Look for `permissionDecision: "deny"` after the change, or `"ask"` at the default.
This writes ordinary local hook state but runs no `npm` command. It tests the
Python handler, not delivery through your agent host.

## 4. Add local intent without pretending it is enforced

Suppose your team requires migration review. Add the project-specific wording,
route it to your migrations, cite the team policy, rebuild, and use `explain` on a
migration file. That makes the guidance available where it matters.

If the requirement is "never run a production migration without approval", the
words are not enough. The current command detector cannot infer every production
database target. You need an appropriate executable guard or a restricted tool
that can recognize that boundary. Add positive and negative cases to its tests,
and report exactly which operations it covers.

You can change existing check modes in TOML. Adding a genuinely new check requires
code in the hook implementation and its literal `CHECKS` declaration, a principle
binding, appropriate event wiring, and tests. Safety Core does not currently offer
an arbitrary policy language or compile natural language into enforceable policy.

## 5. Keep changes deliberate and inspectable

Change the authored rulebook; rebuild the generated files. Record why a meaningful
rule changed in the commit or review. Preserve unrelated project settings. The
existing checks compare generated regions with their source and expose missing
bindings or weaker-than-declared modes.

The map shows configuration. Session records show selected observed tool results.
They are separate surfaces: the current map is not a session replay or an automatic
account of which instructions influenced an agent's reasoning.

For portable rule files, `build --export rulesync` writes Rulesync inputs. Install
and test Rulesync separately if your project wants its additional targets. Do not
infer a target's runtime protection from the existence of exported instructions.

## A useful acceptance check

Before adopting a customized setup, demonstrate an ordinary edit that proceeds,
a named consequential action that asks or denies, the same action after a mode
change, and an inaccurate final claim contradicted by a recorded failure. Also
test unrecognized actions and missing wiring so their limits remain visible.

Protocol tests can be deterministic and need no API key. Separately exercise the
configured agent host when making claims about that host's runtime integration.
