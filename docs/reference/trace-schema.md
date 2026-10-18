# Trace schema: `doctrine-map/trace@1`

`python3 doctrine.py trace .doctrine/sessions/<session id>/` reads one session's hook record
and writes it as ordered steps joined to the rules. `python3 doctrine.py map --trace FILE`
draws it over the map (see [the map guide](../guides/map.md#session-traces)).

A trace shows what the Safety Core hooks recorded: commands and how they exited, files read
and edited, and what the hooks said. It does not show what the model read in its
instructions, what it was thinking, or why it chose an action. Only Bash commands, Read and
the edit tools are recorded; other tool calls (Glob, Grep, web fetches) appear only when a
hook said something about them.

```json
{
  "schema": "doctrine-map/trace@1",
  "generated_at": "2026-10-18T23:11:00Z",
  "session": "4ba03179-...",
  "repository": {"name": "hook_rules_haiku_1", "files_total": 22, "commit": "6ceea3f"},
  "started": 1792364753.6, "ended": 1792364771.8,
  "records": ["receipts.jsonl", "edits.jsonl", "reads.jsonl", "decisions.jsonl", "once/"],
  "boundary": "Shows what the Safety Core hooks recorded in this session: ...",
  "steps": [],
  "touched": {"files": [], "places": [], "routes": []},
  "principles": {"reached_agent": [], "asked_person": [], "told_person": [], "on_touched_routes": []},
  "checks": [{"check": "bypass_checks", "decision": "ask"}],
  "counts": {},
  "graph": {"schema": "doctrine-map/graph@1"}
}
```

`started` and `ended` are Unix times from the session's `started` and `last_stop` files.
`graph` is the [map graph](graph-schema.md) of the repository's configuration **when the
trace was made**, not necessarily when the session ran; `--no-graph` leaves it out. Ids in
`steps`, `touched` and `principles` are graph node ids (`route:tests`, `place:tally`, `P1`).

## Inputs

| Session file | Becomes |
|---|---|
| `receipts.jsonl` | `command` steps with `exit`, `status` and `checks` |
| `edits.jsonl`, `reads.jsonl` | `edit` and `read` steps, one file each |
| `decisions.jsonl` | `decisions` on the step of the same tool call; Stop and SessionStart rows become `stop` and `session` steps |
| `once/route-*` | for sessions recorded before `decisions.jsonl` existed, a `reminder` step at the marker's time |

Records of one tool call are joined by Claude Code's `tool_use_id`. Records without one stay
separate steps. Rows from one Stop event within three seconds form one `stop` step.

## Steps

| Field | Meaning |
|---|---|
| `n` | position, from 1, in time order |
| `at` | seconds after the session record began |
| `kind` | `read`, `edit`, `command`, `stop`, `session`, `reminder` or `tool` |
| `tool`, `label` | the tool, and the path or command (as recorded: commands are cut at 300 characters, key shapes already `[redacted]`) |
| `files` | `{path, how, routes, place}` for each file or folder the step touched; `how` is `read`, `edited`, `named` (a literal path in a command) or `asked about` |
| `routes`, `places` | route and place ids of those files and of the step's decisions |
| `exit`, `status`, `checks` | command steps: the exit code Claude Code reported, the worst status of its recognised test, build or git commands (`failed`, `masked`, `unknown`, `ok`) and each of them |
| `decisions` | `{event, check, decision, principles, routes, said}`: what a hook returned for this call |
| `ran` | `true` when a receipt, edit or read shows the call ran; `false` when a check asked or denied and no record shows it ran; `null` otherwise |

`decision` is one of `ask` (a person was asked), `deny` (the call was refused), `block` (a Stop
hook kept the agent working), `remind` (a note to the agent) and `advise` (a note to the
person). `said` is the first 400 characters of the text the hook returned, redacted.
`ran: false` means only that no receipt, edit or read of that call exists. In a
non-interactive run Claude Code denies every ask; with a person present, an approved call
runs and is recorded under the same `tool_use_id`. Read it as "no record that it ran".

## Summary fields

- `touched`: every file, place and route that appears in a step.
- `principles.reached_agent`: principles named by a `remind`, `deny` or `block`, whose text
  went to the agent. `asked_person` from `ask`, `told_person` from `advise`.
  `on_touched_routes` lists the principles the touched routes carry, whether or not a
  reminder was sent: a route delivers on its own triggers (`read`, `edit`, `shell`), once per
  session.
- `checks`: each check and decision that occurred. `counts`: steps, commands that ran, failed
  commands, edits, reads, `not_run` steps and each decision.

## Privacy

The trace replaces the repository's absolute path with `.` and the home folder with `~`.
Commands are redacted by the hooks before they are recorded; nothing in the session record
holds a key-shaped value. Review a trace before sharing it: commands and file names can
still describe private work.

## Samples

[agent-runs-20261018-trace-hook.json](agent-runs-20261018-trace-hook.json) and
[agent-runs-20261018-trace-claim.json](agent-runs-20261018-trace-claim.json) are traces of
two Claude Haiku runs from the [18 October agent runs](agent-runs-20261018.md) setup
(`run_one.sh hook rules 1` and `claim rules 1`), recorded with the decision log.
