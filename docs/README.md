# Documentation

Start with the [repository introduction](../README.md) and the
[adoption walkthrough](guides/adoption.md).

| Directory | Reader and responsibility |
|---|---|
| [guides/](guides/) | Adoption, agent setup and using the rule map. |
| [reference/](reference/) | Graph format, research foundations, dated host observations and recorded agent runs. |
| [maintainers/](maintainers/) | Implementation design and hook behaviour, including limits. |
| [img/](img/) | Current README and map-guide captures, with provenance in [map-captures.json](maintainers/map-captures.json). Keep their original aspect ratios. |

The [design guide](maintainers/design.md) maps the source. The
[agent setup guide](guides/agent-setup.md) is also the plugin skill's entry.
The source viewer is [viewer/map.html](../viewer/map.html); adoption copies it to
`.doctrine/map.html` so existing installed commands keep working.

Repository placement is checked by `python3 scripts/check_repository_structure.py`
and regression fixtures in `tests/test_repository_structure.py`. These use Git's
index and nonignored new files, excluding local generated output. Keep the small
CLI and runtime hooks together at the root; tooling for maintaining this repository
belongs in `scripts/`, and tests belong in `tests/`.

Keep only consumed captures in `img/`: when a preview is replaced, update its
guide and capture record, then remove superseded images. The structure check
rejects orphaned images and references to missing captures. Earlier UI captures
remain available in Git history; recorded experiment evidence stays in `reference/`.
