---
paths:
  - ".github/workflows/**"
  - ".github/workflows"
  - "**/.gitlab-ci.yml"
  - "**/.gitlab-ci.yml/**"
  - ".circleci/**"
  - ".circleci"
  - "**/Jenkinsfile"
  - "**/Jenkinsfile/**"
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yaml/**"
---
<!-- doctrine-map:generated from doctrine.toml by doctrine.py build. Do not edit; change doctrine.toml and rebuild. -->
# Doctrine route: ci

These files define the checks people rely on to oversee changes. Disabling or weakening a check needs a person.

## P1 Leave the checks on [ask]

Do not switch off, skip or weaken the checks that let people oversee changes.

Hooks, CI, pre-commit checks and logs are how people see what agents do. Skipping them (--no-verify, disabling hooks, deleting workflow steps or logs, or rerunning a failed check with an invented setting) needs a person's say-so. If a check is wrong, say so instead of routing around it.

## P2 Ask before irreversible or publishing actions [ask]

Irreversible or publishing actions wait for a person.

Force pushes, history rewrites, hard resets, deleting branches or data, migrations against shared databases, infrastructure apply or destroy, deploys and package publishing cannot be undone cheaply. The agent says what will happen and asks first. Reversible work goes ahead.
