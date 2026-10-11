# Claude's constitution: clauses

`clauses.json` holds 38 verbatim excerpts from Claude's constitution. Each has an id, the title of its section and an anchor URL into the source page.

- Source: https://www.anthropic.com/constitution
- Published: 21 January 2026. Retrieved: 11 October 2026.
- Licence: CC0 1.0 Universal. The source page releases the constitution under a Creative Commons CC0 1.0 Deed, so "it can be freely used by anyone for any purpose without asking for permission".
- This project is not affiliated with or endorsed by Anthropic.

`source/constitution.md` is the markdown rendering of the source page that the clauses were extracted from. It was produced with the Jina reader (r.jina.ai) on 11 October 2026 and is kept byte for byte. The stored clause text has markdown emphasis markers removed and nothing else changed.

## Re-extract and verify

```
python3 sources/anthropic-constitution/extract_clauses.py sources/anthropic-constitution/source/constitution.md /tmp/clauses.json
cmp /tmp/clauses.json sources/anthropic-constitution/clauses.json
```

The extractor finds each clause by a start phrase and an end phrase, and stops with an error if either is missing. To check the clauses against the live page, make a fresh markdown rendering of the source URL and run the same two commands on it. Any difference means the page has changed.
