---
name: doctrine-map
description: Give a repository one doctrine for its AI agents and report honestly what holds. Use when someone asks to set up, adopt, audit or explain the rules agents follow in a repository (AGENTS.md, CLAUDE.md, .claude/rules, hooks), to check which rules are enforced and which are only words, to see what an agent receives at a path, or to open the doctrine map. The steps are in program.md; doctrine.py does the work.
---

# doctrine-map

Read `${CLAUDE_PLUGIN_ROOT}/program.md` and follow it. Outside the plugin, it is
`program.md` at the root of the doctrine-map repository.

In short:

1. The person owns the doctrine. You do the wiring and report what holds.
2. Set up the repository once:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/doctrine.py" init --target .
   ```

3. Then work with `python3 .doctrine/doctrine.py`:
   - `check`: errors, warnings and the coverage table; it ends with
     "N of M principles enforced beyond words".
   - `build`: rewrites the generated files after you change `.doctrine/doctrine.toml`.
   - `explain <path>`: exactly what an agent receives at a path.
   - `map --serve --open`: the live map.
4. Never edit generated files, and never change a principle's declared level to make
   `check` pass. Rule changes wait for the person.
5. Report the coverage line, the prose-only principles and what needs the person.
