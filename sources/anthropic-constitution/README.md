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


## How these ideas become repository behavior

The reference doctrine adapts selected constitutional ideas. Clause IDs below
refer to `clauses.json`; A/P identifiers refer to the existing `doctrine.toml`.
The runtime reads the local doctrine and executes Python checks, not this excerpt
collection. A citation explains a rule's origin; it is not its enforcement.

| Local rules | Excerpt IDs | What implements the adaptation |
|---|---|---|
| A1, P1: oversight | `safe.no-undermining-correction`, `safe.no-hiding-from-oversight` | Ask about recognized check-bypass commands. |
| A2, P2-P4: consequences and useful autonomy | `safe.if-in-doubt-dont`, `helpful.never-trivially-safe`, `helpful.no-excess-check-ins`, `judgment.raise-concerns-before-not-midway` | Selected command prompts, permission-question advice and unreported-dirty-work advice. P2 inherits the constitutional connection through A2; its direct sources are other guidance. |
| A3-A4, P5-P6, P8: evidence | `honest.truthful`, `honest.calibrated`, `honest.non-deceptive` | Shell-status reminders, session records, selected claim checks and documentation reminders. |
| P7: meaningful tests | `helpful.no-special-cased-tests` | A routed reminder; no semantic test-quality checker. |
| P9: learn from mistakes | `flaws.take-ownership`, `flaws.without-anxiety` | An error-log command and limited advisory detection of unlogged admissions. |
| P10: disclose reduced scope | `helpful.no-silent-watering-down` | Written guidance only. |
| A5: limited authority | `safe.no-excess-resources` | Supports P11-P13; their direct sources use OpenAI, OWASP and OpenSSF guidance. Selected secret checks and reminders do not restrict host access. |
| A7, P15: sanctioned rule changes | `safe.no-unsanctioned-self-modification` | Ask about recognized rule-file writes; check generated instructions for drift. |

A6 and P14 are repository-engineering choices about linking rules to places and
mechanisms. They draw on agent-tool documentation and other guidance, rather than
a direct Constitution excerpt. See [foundations](../../docs/reference/foundations.md) for the
research and upstream implementation precedents.

The official January 2026 Constitution is also available as a
[versioned Markdown source](https://github.com/anthropics/claude-constitution/blob/84fa9a2711837780ffdddf9d9f32820c92f92ede/20260120-constitution.md),
under CC0. That reference was checked on 13 October 2026. The earlier stored
rendering above remains the source of this repository's extracted clauses.
