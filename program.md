# Safety Core: agent setup guide

This file tells an AI agent how to give a repository a doctrine and how to report what
actually holds. Read it top to bottom before you start.

## Who does what

- **The person** owns the doctrine. They write it, or adopt the reference doctrine in
  `doctrine.toml`, and they decide every principle's enforcement level. Rule changes wait
  for them.
- **You, the agent,** do the wiring. You find the rules the repository already has, attach
  principles to the places they govern, build, check, close the gaps you can, label the
  rest honestly, and report.

The goal is simple: every rule an agent works under is either enforced, delivered where it
applies, or shown plainly as words. Report the coverage that `check` prints, even when it
is low.

## Setup

1. Read `README.md`, then `doctrine.toml` (the reference doctrine: 7 axioms, 15 principles,
   9 routes and the sources they cite).
2. In the target repository, run:

   ```
   python3 path/to/safety.py init --target .
   ```

   This copies `doctrine.toml`, `doctrine.py`, `hooks.py` and `map.html` into `.doctrine/`,
   keeps only the routes that match files here, wires the hooks into
   `.claude/settings.json` without removing anything already there, and builds. From now
   on the commands are `python3 .doctrine/safety.py <command>`.
3. Run `python3 .doctrine/safety.py check` once and keep the output. It is your baseline.

If the repository already has a doctrine, skip `init` and start at the loop.

## What you may change

- `.doctrine/doctrine.toml`: routes, reminders, and the `enforced_by` lists, as the loop
  below describes.
- New principles, only with the person's agreement. Each one needs an anti-principle, at
  least one axiom it serves, and a source when the claim rests on one.

## What you must not change

- Generated files: the managed region in `AGENTS.md`, the one in `CLAUDE.md`, and
  `.claude/rules/doctrine-*.md`. Change `doctrine.toml` and rebuild instead. `check` fails
  on any hand edit.
- A principle's declared level, to make `check` pass. If a level does not hold, say so and
  ask the person whether to lower it or to add an enforcer.
- `hooks.py` or `.claude/settings.json`, to silence a check.
- The axioms, the anti-principles, or the meaning of a principle. These are the person's.

## The loop

1. **Inventory.** List every rule the repository already gives agents or contributors:
   `AGENTS.md` and `CLAUDE.md` at any depth, `.claude/rules/`, `.cursor/rules/`,
   `.cursorrules`, `.github/copilot-instructions.md`, `.github/instructions/`,
   `CONTRIBUTING.md`, `CODEOWNERS`, pre-commit configuration, and the CI workflows. Note
   for each rule where it lives and whether anything enforces it.
2. **Map.** For each rule, find the reference principle it already expresses. If none fits,
   draft a local principle with its anti-principle and bring it to the person. Rules that
   contradict a principle go to the person too; do not resolve them yourself.
3. **Route.** Read the coverage table in the `check` output and the `unrouted_sensitive`
   warnings. Add or widen routes so each place that matters receives its principles: CI,
   infrastructure, migrations, secrets, release scripts, tests, dependency manifests,
   documentation, and anything specific to this repository. Write each reminder as a fact
   about the place, such as "Files here change database structure".
4. **Build.** `python3 .doctrine/safety.py build`.
5. **Check.** `python3 .doctrine/safety.py check`. Errors fail it: an enforcer that does
   not exist, a generated file that differs from a fresh build, an entry card over its
   budget. Warnings do not: a route that matches nothing, a sensitive place no route
   reaches.
6. **Close or label each gap.**
   - Missing enforcer: point the principle at a check that exists (a `hooks.py` check, a
     route, `check:links`), or ask the person whether to lower its declared level.
   - Dead route: fix its paths, or remove it if the place does not exist here.
   - Unrouted sensitive place: add a route, or tell the person why none is needed.
   - Over budget: shorten the `one` lines, or ask the person which principles can leave
     the entry card.
   Then go back to step 4. Stop when `check` passes, or when every remaining error needs
   the person.
7. **Explain.** Run `python3 .doctrine/safety.py explain <path>` for the two or three
   riskiest paths (a migration, a workflow, an infrastructure file). Read what an agent
   receives there and fix anything surprising.
8. **Map.** Run `python3 .doctrine/safety.py map --serve --open` for a live map, or
   `map --out doctrine-map.html` for one file to share. Hide what is only words to see the
   doctrine as the repository enforces it.

## External guards

If the repository already runs nah, cc-safety-net or destructive_command_guard (dcg) as
Claude Code hooks in `.claude/settings.json`, `check` credits them for the checks they do
by default and names them with `by`. Cupcake enforces only the policies written for it, so
it counts only where a principle names `guard:cupcake` in `enforced_by`. Do not remove a
guard that already runs.

## The report

End with a short report for the person, in this order:

1. The coverage line from `check`, word for word: "N of M principles enforced beyond
   words".
2. The coverage table, or the rows that changed.
3. Every principle that is prose only, by id and name. These are rules agents read and
   nothing enforces.
4. What you changed in `doctrine.toml`, route by route.
5. What needs the person: proposed principles, conflicts, levels that do not hold.
6. What you did not check or could not do, and why.

Use the numbers `check` printed. Do not round them up, and do not describe a rule as
enforced unless `check` says so.

## Notes

- Hooks are a guardrail for a trusted but fallible agent. They are not a sandbox or a
  security boundary. Say so if the person asks what the hooks protect against.
- `check` runs in CI. A build that someone forgot to run fails there, which is the point.
- `python3 .doctrine/safety.py log-error "<what happened>" --principle P9 --lesson
  "<rule learned>"` records a mistake that reached the person or the repository.
