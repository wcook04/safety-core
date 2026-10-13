# Graph schema: `doctrine-map/graph@1`

`python3 doctrine.py build` writes `.doctrine/graph.json`. The map viewer reads only this
file, so the engine and the viewer meet here. `python3 doctrine.py map --serve` serves the same JSON
at `/graph.json` and announces each rebuild on `/events` (server-sent events, one
`data: {"rebuilt": "<generated_at>"}` line per rebuild).

All ids are stable across rebuilds so the viewer can keep its layout and selection when
the doctrine changes.

```json
{
  "schema": "doctrine-map/graph@1",
  "generated_at": "2026-10-11T15:40:00Z",
  "repository": {"name": "example", "commit": "abc1234", "files_total": 412},
  "doctrine": {
    "name": "safety-core", "version": "0.1.0", "summary": "...",
    "source": "doctrine.toml", "sha256": "..."
  },
  "entry": {"lines": ["..."], "budget": 40, "used": 30},
  "nodes": [],
  "edges": [],
  "gaps": [],
  "coverage": {}
}
```

## Nodes

Every node has `id`, `kind` and `name`. Kind-specific fields:

| kind | id form | fields |
|---|---|---|
| `axiom` | `A1` | `clause`, `plain`, `anti`, `sources` (list of `{ref, at, quote}`) |
| `principle` | `P2` | `one`, `three`, `anti`, `axioms`, `declared` (level written in the doctrine), `effective` (strongest level actually present; at least `remind` when a live route carries it), `enforcers` (list of `{ref, status, level}`, status `present` or `missing`; an external guard's entry also has `by`, the tool's name), `global` (true when no live route carries it), `sources` |
| `route` | `route:migrations` | `paths`, `reminder`, `on` (`read`, `edit`, `shell`), `principles`, `matches` (number of files matched) |
| `place` | `place:db/migrations` | `path`, `is_dir`, `files` (files beneath it), `sensitive` (matches a built-in sensitive pattern), `routes`, `principles` (everything an agent receives there, entry principles excluded) |
| `enforcer` | `enf:hook:pre_tool#irreversible` | `ref`, `type` (`hook`, `stop`, `check`, `cli`, `route`, `guard`), `level` (null when missing), `status`, `file` |
| `source` | `src:anthropic.constitution` | `title`, `publisher`, `date`, `url`, `licence`, `quote_policy` |

Places are directories at depth one or two, plus single files at the repository root
that a route or a built-in sensitive pattern matches, so the map stays readable on large repositories. A place's
`files` counts every file beneath it.

## Edges

| kind | from → to | meaning |
|---|---|---|
| `serves` | principle → axiom | the principle is one way the axiom is kept |
| `applies` | route → principle | the route delivers this principle |
| `governs` | route → place | the route's paths match files in this place; `matches` counts them and `matched_files` lists their repository-relative paths |
| `enforced_by` | principle → enforcer | this mechanism enforces the principle |
| `cites` | axiom or principle → source | the claim rests on this published source |

New graphs include exact membership on every `governs` edge. This is an additive
`graph@1` field: viewers accept older edges without it and retain their links.
A viewer may omit a parent link only when the union of its descendant memberships
equals the parent's membership. Counts alone do not establish that equality.

## Gaps

Each gap is `{kind, id or path, detail}`. `missing_enforcer` and `prose_only` carry the
principle's id; `unrouted_sensitive` carries both the place's node id and its path:

| kind | raised when |
|---|---|
| `prose_only` | a principle's effective level is `prose` |
| `missing_enforcer` | a principle names an enforcer that does not exist |
| `dead_route` | a route matches no file |
| `unrouted_sensitive` | a place matches a built-in sensitive pattern (CI, infrastructure, migrations, secrets, release) but no route |
| `stale_projection` | a generated file differs from a fresh build |
| `over_budget` | the entry card is longer than its budget |

## Coverage

```json
{
  "axioms": 7, "principles": 15,
  "by_level": {"block": 2, "ask": 3, "check": 1, "remind": 5, "advise": 3, "prose": 1},
  "enforced_beyond_words": 6,
  "files_total": 412, "files_governed": 96,
  "routes_live": 7, "routes_dead": 2
}
```

`enforced_beyond_words` counts only `block`, `ask` and `check`. Reminders and advice are not enforcement. Hook source may be `present` with `level: null` when unwired, off or record-only. Hook levels reflect repository event wiring and mode overrides, not an observed host execution.
