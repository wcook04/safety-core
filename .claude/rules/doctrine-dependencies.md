---
paths:
  - "**/package.json"
  - "**/package.json/**"
  - "**/requirements*.txt"
  - "**/requirements*.txt/**"
  - "**/pyproject.toml"
  - "**/pyproject.toml/**"
  - "**/go.mod"
  - "**/go.mod/**"
  - "**/Cargo.toml"
  - "**/Cargo.toml/**"
  - "**/Gemfile"
  - "**/Gemfile/**"
---
<!-- doctrine-map:generated from doctrine.toml by doctrine.py build. Do not edit; change doctrine.toml and rebuild. -->
# Doctrine route: dependencies

This file decides what third-party code runs. New dependencies are named in the summary and checked to exist.

## P13 Use only the access the task needs [remind]

Do not reach for unrelated credentials, services or new dependencies; name any dependency you add.

Every extra permission is another way for a mistake to spread. Work inside the task's scope. New dependencies are named in the summary and checked to exist, because hallucinated or malicious packages are a known supply-chain risk.
