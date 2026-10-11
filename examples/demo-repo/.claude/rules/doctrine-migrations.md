---
paths:
  - "**/migrations/**"
  - "**/migrations"
  - "**/*.sql"
  - "**/*.sql/**"
  - "alembic/**"
  - "alembic"
  - "prisma/migrations/**"
  - "prisma/migrations"
  - "db/**"
  - "db"
---
<!-- doctrine-map:generated from .doctrine/doctrine.toml by doctrine.py build. Do not edit; change .doctrine/doctrine.toml and rebuild. -->
# Doctrine route: migrations

Files here change database structure. Applying them to a shared database cannot be undone cheaply, and this repository asks a person first.

## P2 Ask before irreversible or publishing actions [ask]

Irreversible or publishing actions wait for a person.

Force pushes, history rewrites, hard resets, deleting branches or data, migrations against shared databases, infrastructure apply or destroy, deploys and package publishing cannot be undone cheaply. The agent says what will happen and asks first. Reversible work goes ahead.

## P4 Keep the work recoverable [advise]

Work in small, committed steps and leave a clean state; raise concerns before starting, not midway.

Small commits with clear messages let a person undo one step. A half-finished change can do more harm than finishing or never starting, so concerns are raised before work begins. At the end the tree is clean or the leftovers are named.
