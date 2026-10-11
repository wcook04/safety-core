---
paths:
  - "scripts/release*"
  - "scripts/release*/**"
  - "release/**"
  - "release"
  - ".github/workflows/release*"
  - ".github/workflows/release*/**"
  - "**/CHANGELOG*"
  - "**/CHANGELOG*/**"
---
<!-- doctrine-map:generated from doctrine.toml by doctrine.py build. Do not edit; change doctrine.toml and rebuild. -->
# Doctrine route: release

These steps publish work to other people. Publishing waits for a person.

## P2 Ask before irreversible or publishing actions [ask]

Irreversible or publishing actions wait for a person.

Force pushes, history rewrites, hard resets, deleting branches or data, migrations against shared databases, infrastructure apply or destroy, deploys and package publishing cannot be undone cheaply. The agent says what will happen and asks first. Reversible work goes ahead.
