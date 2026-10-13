# Reading the map

The map shows your doctrine and your repository's configuration in one picture: which
principles a route associates with which parts of the code, what mechanism is configured
for each principle, and where the configuration differs from what the doctrine declares.
It shows configuration. It does not show what an agent did.

![The map tracing the tests route in demo-repo, light theme](img/map-20261013-light.png)

## Opening it

- `doctrine.py map --serve` runs the map on your computer. It redraws each time you
  save doctrine.toml or move files, and keeps your selection, zoom and position.
- `doctrine.py map --out doctrine-map.html` writes a single file with the graph inside.
  It opens from disk with no network access.
- If you open `map.html` with no graph, it shows the sample in
  `examples/graph.sample.json`. The header then says "Sample data".

## The four columns

Read the map from left to right.

1. **Axioms.** The root commitments, at most seven. Each one is a bar that spans the
   principles serving it.
2. **Principles.** The working rules, each with its full title and, beneath it, the
   configured mechanism and any difference from the declared one.
3. **Routes.** A route associates principles with paths.
4. **Places.** The directories at depth one and two, plus root files that a route
   matches, listed as a file tree. The count is the files inside each place, so a
   folder and its subfolder can show the same files; do not add rows together.
   Route details show matched-file counts. A redundant parent link is omitted only
   when all of its matched files are represented by its children.

## Tracing one route

The map draws the connections of one route at a time. On opening, it traces a populated
route, chosen by principle count, then the fewest representative places, then id, so the same graph always opens the same way; add
`#route=tests` to the address to choose one. The bar above the map names the traced
route and how many principles, places and matched files it has.

- **Click a route** to trace it. Lines run in from the principles it carries and out to
  the places it matches. Hovering over a route previews its connections.
- **Click a principle or place** to read it. This does not expand the drawing into its
  other routes; the side panel lists them, and each one can be traced.
- **Clear** removes the trace. **Show all connections** draws every route at once, for
  checking the whole topology.

A principle that no route carries has a hollow end and the label "repo-wide". It
applies through the entry card, and through a repository-wide check where one is
configured.

## On a phone

Below 600 pixels, a route selector and readable lists replace the small drawing.
Choose a route to see its full principle titles, configured mechanisms and matched
places. Tap a principle or place to read its details below. Routes with no matching
files remain selectable and explain the empty result. Wider screens retain the map.

## Configured mechanisms

Each principle shows one label for the mechanism the repository configuration provides.
The labels are categories, not points on a score:

| Label | Meaning |
|---|---|
| block | A hook refuses the action. |
| ask | A hook stops and asks a person. |
| check | CI or the doctrine check fails. |
| remind | A factual reminder reaches the agent where it works. |
| advise | A note to the person at the end of a turn. |
| written | Written down only. |

Block, ask and check are drawn filled, remind and advise outlined, and written dashed.
When the doctrine declares a different mechanism from the one configured, the row adds
"declared ask" (for example) in a muted warm colour. The panel then says
"Configuration differs". Changing a rule's wording does not add a mechanism; a hook or
check has to be configured for the label to change.

## Configuration notes

The side panel's overview lists three kinds of note, kept apart:

- **Declared and configured differ:** the doctrine names a stronger mechanism than the
  repository provides.
- **Wiring:** a named enforcer that is missing, a route that matches no file (shown in
  place as "0 matched files"), a sensitive place with no route, a stale generated file
  or an entry card over budget.
- **Written guidance only:** principles delivered by the entry card alone. That can be
  the right choice for a judgment call that no hook can check.

## The strip across the top

The strip names the snapshot and reads "N of M principles have a block, ask or check
configured", then gives the count for each mechanism, zeros included. Hover over a
mechanism to pick out its principles. The line beneath says that execution is not
assessed, and gives the files under a route, the routes that match files, and the
length of the entry card against its budget.

## The side panel

- A **route** shows its paths, how many files it matched, when it is delivered, the
  principles it carries with their own mechanisms, its reminder and the places it
  matches.
- A **principle** shows its one-line rule, then the configured and declared
  mechanisms, where it applies, and that execution is not assessed. Below that come
  what its mechanism does not establish, the failure it rejects, its sources (cited
  directly, then those inherited through its axioms) and the mechanisms it names.
- An **axiom** shows its plain reading, its clause, what it rejects, the principles
  serving it and its sources.
- A **place** lists what the configuration associates with it: the entry card, each
  route's reminder and principles, then the repository-wide principles.

**Only block, ask or check** fades every principle configured as a reminder, advice or
written guidance. **View from one place** picks a place and fades everything the
configuration does not associate with it. **Zoom** with the buttons, by pinching on a
trackpad, or with ctrl or cmd and the scroll wheel; drag to pan; "Fit" or the 0 key
resets the view.

## Keyboard

Tab moves into the map. The arrow keys then move within a column (up and down) and
between columns (left and right). Enter or Space opens the focused mark, and on a route
traces it. Escape returns the panel to the overview, and a second press leaves View from
one place. The + and - keys zoom.

## Layout

The layout is computed from the ids and the paths alone, with no simulation, so the same
doctrine always gives the same picture. Principles are grouped under their first axiom
in id order, and each row is sized to its wrapped title. Places are sorted by path.
Routes are ordered by the rows they join and spread evenly down the principle column,
so each label has its own space; selection never moves them. When the doctrine changes,
marks glide to their new rows, new marks fade in and removed ones fade out.

## Review captures

`python3 scripts/build_map_examples.py --out /tmp/safety-map-review` builds standalone
snapshots from the included demo. The `empty` snapshot adds only a synthetic `unused`
route with paths `unused/**`; the real demo remains unchanged. Each snapshot has a
light variant (the viewer’s existing light theme) and a dark variant (its dark media
rule enabled), so captures do not depend on desktop preferences.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/map-empty-20261013-dark.jpg">
  <img src="img/map-empty-20261013-light.jpg" alt="An empty route showing its two principles and zero matched files" width="1280">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/map-phone-20261013-dark.jpg">
  <img src="img/map-phone-20261013-light.jpg" alt="The phone route selector with readable principles and matched places, with route details below" width="390">
</picture>

These additional captures use the same demo source plus the declared empty-route
fixture. Phone captures use a 390 by 844 viewport; empty-route captures use 1280 by 900.
Run `node scripts/test_map_model.js` for lossless aggregation and old-snapshot fixtures.

## For the engine

`map.html` is one self-contained file: the CSS and JavaScript are inline and it makes no
external requests. It reads only `doctrine-map/graph@1` (see
[GRAPH_SCHEMA.md](GRAPH_SCHEMA.md)) and loads it in this order:

1. JSON inside `<script id="doctrine-graph" type="application/json"></script>`. To
   build a static map, replace that empty element with one holding the graph. Escape
   `</` as `<\/` inside the JSON.
2. `./graph.json`, fetched from the server. When it loads, the map also listens on
   `./events` for server-sent events and fetches the graph again on each message.
3. `./examples/graph.sample.json`.

## Coverage boundary

Only `block`, `ask` and `check` count as enforced. Reminders and advice remain visible
but do not enter that total. Hook credit requires repository event wiring and respects
mode overrides; it is a configuration report, not proof of execution in an agent host.
