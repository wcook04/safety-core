# Contributing to Safety Core

Useful changes make a rule easier to understand, expose a mismatch between a
declared rule and its checks, or improve setup in an ordinary coding project.

For a bug, [open an issue](https://github.com/wcook04/safety-core/issues) with
the command, Python version, expected behaviour and a small reproduction.
Use an invented example; omit credentials, private prompts and session logs.
Report vulnerabilities through [the private security route](SECURITY.md).

## Make a change

1. Work in a branch and keep the change focused.
2. Edit the source. Rules live in `doctrine.toml`; generated sections of
   `AGENTS.md`, `CLAUDE.md` and path rule files come from `python3 safety.py build`.
   Explain a proposed rule change and its tradeoff so the maintainer can decide.
3. Check the change from the repository root:

   ```sh
   python3 safety.py check
   python3 -m unittest discover -s tests
   ```

4. Open a pull request explaining the behaviour before and after the change,
   what you tested, and any limits. Disclose material AI assistance.

For a new hook check, include a case it should catch and an ordinary action it
should allow. Keep the standard-library setup and distinguish a reminder from
an action the configured host actually blocks. The [design guide](docs/maintainers/design.md)
maps the source files and [hook guide](docs/maintainers/hooks.md) explains runtime behaviour.

The code is [MIT licensed](LICENSE). Keep source credits and respect differing
terms for any material you add. Discuss the work respectfully and keep reports
reproducible; this is a small project maintained by Will Cook.

## Feedback contributions

Thanks to [Skitter's public replay report](https://swarmmemo.com/e/b7b596e955f0949c4f93df6d8d929053)
for requesting approval on each secret-path read and clearer deletion reasons
when a sandbox's home resolves to the filesystem root. The report covers a
pinned disposable Linux demo, without a live agent host; it is feedback credit,
not an endorsement.
