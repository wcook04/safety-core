# Reading the map

The map shows your doctrine and your repository in one picture. You can use it to see
which rules reach which parts of the code, how strongly each rule holds, and where the
gaps are.

![The map at 1440 by 900, light theme](img/map-1440x900-light.png)

## Opening it

- `doctrine.py map --serve` runs the map on your computer. It redraws each time you
  save doctrine.toml or move files, and keeps your selection, zoom and position.
- `doctrine.py map --out doctrine-map.html` writes a single file with the graph inside.
  It opens from disk with no network access.
- If you open `map.html` with no graph, it shows the sample in
  `examples/graph.sample.json`. The header then says "Sample data".

## The four columns

Read the map from left to right.

1. **Axioms.** These are the root commitments, at most seven. Each one is a heavy bar
   that spans the principles serving it.
2. **Principles.** These are the working rules. Under each name, in quieter italics, is
   its anti-principle, the opposite failure the rule must not slide into.
3. **Routes.** A route attaches principles to paths. Lines come in from the principles
   a route carries and go out to the places it matches.
4. **Places.** These are the directories at depth one and two, plus root files that a
   route matches. They are listed as a file tree with a file count for each.

A line into a place means that an agent working there receives the principle as a
reminder. A principle that no route carries shows a hollow end and the word
"everywhere". It reaches agents through the entry card and through hooks that apply
across the whole repository.

## How strongly a rule holds

Five cells beside each principle work as a gauge. The more cells are filled, the
stronger the mechanism that exists for the rule:

| Cells | Level | Meaning |
|---|---|---|
| 5 | block | A hook refuses the action. |
| 4 | ask | A hook stops and asks a person. |
| 3 | check | CI or the doctrine check fails. |
| 2 | remind | A factual reminder reaches the agent where it works. |
| 1 | advise | A note to the person at the end of a turn. |
| 0 | prose | Written down only. The gauge is empty and the row says "only words". |

The gauge shows the level that actually exists, not the level the doctrine declares. If
the doctrine declares more than exists, the missing cells are drawn as dashed outlines
and the row says, for example, "declared ask". The level reads from the shape and the
fill alone, so colour is never needed to tell levels apart.

## Gaps

Each gap is marked where it occurs, in one muted warm colour, and listed in the side
panel:

- **Only words:** an empty gauge on the principle.
- **Missing enforcer:** "1 enforcer missing" under the principle's level.
- **Route that matches nothing:** a dashed route, with its patterns listed under
  "Routes that match nothing" at the foot of the places.
- **Sensitive place with no route:** a hollow ring and "sensitive, no route" beside the
  place. CI, infrastructure, migrations, secrets and release paths count as sensitive.

A place with no route but nothing sensitive has a plain hollow mark (entry card only).

## The strip across the top

The strip reads "N of M principles enforced beyond words", then gives the count at each
level. Hover over a level to pick out its principles on the map. The figures on the
right give the files under a route, the live and dead routes, the length of the entry
card against its budget, and the number of gaps.

## Interacting

- **Hover** over any mark to trace its links. Everything else dims.
- **Click** a mark to read it in the side panel:
  - An axiom shows its plain reading, its clause, what it rejects, the principles
    serving it, and its sources with quotes and links.
  - A principle shows its one line, its three-line reading, its anti-principle, the
    declared and actual levels, each enforcer and whether it exists, where it is
    delivered, and its sources.
  - A route shows its reminder, its paths and when it fires.
  - A place lists what an agent working there receives: the entry card, then each
    route's reminder and principles, then the principles that apply everywhere.
- **Only what is enforced** fades every principle that is words, reminders or advice, so
  you see what actually holds.
- **Stand here** asks for a place and lets everything not delivered there recede.
  Principles that reach it only as an entry-card line stay half visible.
- **Zoom** with the buttons, by pinching on a trackpad, or with ctrl or cmd and the scroll wheel.
  Drag to pan. "Fit" or the 0 key resets the view.

## Keyboard

Tab moves into the map. The arrow keys then move within a column (up and down) and
between columns (left and right). Enter or Space opens the focused mark. Escape returns
the panel to the overview, and a second press leaves Stand here. The + and - keys zoom.

## Layout

The layout is computed from the ids and the paths alone, with no simulation, so the same
doctrine always gives the same picture. Principles are grouped under their first axiom
in id order. Places are sorted by path. Each route sits between the principles and
places it joins. When the doctrine changes, marks glide to their new rows, new marks
fade in and removed ones fade out.

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
