# Reporting a security issue

Report vulnerabilities privately through
[GitHub's vulnerability report form](https://github.com/wcook04/safety-core/security/advisories/new).
Include the affected commit, a minimal reproduction and the impact you observed.
Use synthetic examples and redact secrets and private session content.

The current `main` branch is the supported development version. Reports are
handled by a solo maintainer on a best-effort basis.

Safety Core's hooks recognise selected command, secret and claim patterns.
They are guardrails, not a sandbox: hooks can be bypassed or fail open, and their
operation depends on the agent host and project configuration. A rule appearing
on the map does not establish that a host executed it. See [hook details](docs/HOOKS.md)
for the implemented checks and limits.

Ordinary bugs and improvements belong in
[issues](https://github.com/wcook04/safety-core/issues); keep vulnerability
details out of public issues until a coordinated disclosure is agreed.
