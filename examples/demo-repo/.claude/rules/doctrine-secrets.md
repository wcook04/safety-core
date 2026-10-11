---
paths:
  - "**/.env"
  - "**/.env/**"
  - "**/.env.*"
  - "**/.env.*/**"
  - "**/*.pem"
  - "**/*.pem/**"
  - "**/*.key"
  - "**/*.key/**"
  - "secrets/**"
  - "secrets"
  - "**/credentials*"
  - "**/credentials*/**"
---
<!-- doctrine-map:generated from .doctrine/doctrine.toml by doctrine.py build. Do not edit; change .doctrine/doctrine.toml and rebuild. -->
# Doctrine route: secrets

This path holds or names credentials. Their values never go into code, commits, logs or messages.

## P11 Keep secrets out [block]

Credentials never go into code, commits, logs or messages.

Keys, tokens, passwords and private keys stay in their stores. Commits are scanned for key shapes and blocked when one appears. A credential the agent happens to find is not permission to use it.
