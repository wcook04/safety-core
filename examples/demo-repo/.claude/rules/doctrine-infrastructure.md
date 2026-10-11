---
paths:
  - "**/*.tf"
  - "**/*.tf/**"
  - "infra/**"
  - "infra"
  - "terraform/**"
  - "terraform"
  - "deploy/**"
  - "deploy"
  - "k8s/**"
  - "k8s"
  - "helm/**"
  - "helm"
  - "**/Dockerfile"
  - "**/Dockerfile/**"
  - "**/docker-compose*.yml"
  - "**/docker-compose*.yml/**"
---
<!-- doctrine-map:generated from .doctrine/doctrine.toml by doctrine.py build. Do not edit; change .doctrine/doctrine.toml and rebuild. -->
# Doctrine route: infrastructure

These files control live systems. Apply, destroy and deploy commands cannot be undone cheaply, and this repository asks a person first.

## P2 Ask before irreversible or publishing actions [ask]

Irreversible or publishing actions wait for a person.

Force pushes, history rewrites, hard resets, deleting branches or data, migrations against shared databases, infrastructure apply or destroy, deploys and package publishing cannot be undone cheaply. The agent says what will happen and asks first. Reversible work goes ahead.

## P13 Use only the access the task needs [remind]

Do not reach for unrelated credentials, services or new dependencies; name any dependency you add.

Every extra permission is another way for a mistake to spread. Work inside the task's scope. New dependencies are named in the summary and checked to exist, because hallucinated or malicious packages are a known supply-chain risk.
