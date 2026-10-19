---
paths:
  - "**/AGENTS.md"
  - "**/AGENTS.md/**"
  - "**/CLAUDE.md"
  - "**/CLAUDE.md/**"
  - ".claude/**"
  - ".claude"
  - ".cursor/**"
  - ".cursor"
  - ".github/copilot-instructions.md"
  - ".github/copilot-instructions.md/**"
  - ".github/instructions/**"
  - ".github/instructions"
  - ".rulesync/**"
  - ".rulesync"
  - ".doctrine/**"
  - ".doctrine"
  - "**/doctrine.toml"
  - "**/doctrine.toml/**"
---
<!-- doctrine-map:generated from doctrine.toml by doctrine.py build. Do not edit; change doctrine.toml and rebuild. -->
# Doctrine route: agent-rules

These files are the rules agents work under. They are generated from doctrine.toml, and changing them needs a person.

## P15 Rule files are generated, and change with a person [ask]

Agent rule files are generated from doctrine.toml; changing the rules needs a person.

AGENTS.md and CLAUDE.md regions, path rules and hook settings are built from doctrine.toml and checked for drift. An agent that edits the rules it works under is changing its own behaviour, so those edits wait for a person.

## P1 Leave the checks on [ask]

Do not switch off, skip or weaken the checks that let people oversee changes.

Hooks, CI, pre-commit checks and logs are how people see what agents do. Skipping them (--no-verify, disabling hooks, deleting workflow steps or logs, or rerunning a failed check with an invented setting) needs a person's say-so. If a check is wrong, say so instead of routing around it.
