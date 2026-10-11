<!-- WILL: opening paragraph in your own words before publishing -->
# repo-constitution (working name)

Status: unfinished. Only the clause source is built. The hooks, the link checker, the renderer and the init command are designed but not written.

What is here:

- `constitution/clauses.json`: 38 verbatim clauses from Claude's constitution (CC0 1.0), each with an id, a section title and an anchor URL. See `constitution/README.md`.
- `constitution/source/constitution.md`: the rendering of the source page the clauses were extracted from.
- `tools/extract_clauses.py`: the extractor. It reproduces `clauses.json` byte for byte from the rendering.
- `docs/DESIGN_NOTES.md`: the design for the parts that do not exist yet, and the Claude Code facts it rests on.

Not affiliated with or endorsed by Anthropic. Code is MIT (see `LICENSE`). The constitution text is CC0 1.0.
