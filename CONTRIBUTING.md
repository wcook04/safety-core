# Contributing to Safety Core

Useful changes make a rule easier to understand, expose a mismatch between a
declared rule and its checks, or improve setup in an ordinary coding project.

For a bug, [open an issue](https://github.com/wcook04/safety-core/issues) with
the command, Python version, expected behaviour and a small reproduction.
Use an invented example; omit credentials, private prompts and session logs.
Report vulnerabilities through [the private security route](SECURITY.md).

## Make a change

1. Work in a branch and keep the change focused.
2. Edit the source. Rules live in `doctrine.toml`; generated sections of
   `AGENTS.md`, `CLAUDE.md` and path rule files come from `python3 safety.py build`.
   Explain a proposed rule change and its tradeoff so the maintainer can decide.
3. Check the change from the repository root:

   ```sh
   python3 safety.py check
   python3 -m unittest discover -s tests
   ```

4. Open a pull request explaining the behaviour before and after the change,
   what you tested, and any limits. Disclose material AI assistance.

For a new hook check, include a case it should catch and an ordinary action it
should allow. Keep the standard-library setup and distinguish a reminder from
an action the configured host actually blocks. The [design guide](docs/maintainers/design.md)
maps the source files and [hook guide](docs/maintainers/hooks.md) explains runtime behaviour.

The code is [MIT licensed](LICENSE). Keep source credits and respect differing
terms for any material you add. Discuss the work respectfully and keep reports
reproducible; this is a small project maintained by Will Cook.

## Audit a parser before changing normalisation

Keep the wrong value the same and vary its container. For route paths, compare
`paths = 42` with `paths = [42]`, then `paths = true` with `paths = [true]`.
Before PR13, the bare number could raise a `TypeError`, while the wrapped
number could be converted to text before validation. Both now produce the
controlled configuration error. The existing regression also checks a mixed
array and an inline table.

Run that paired check from the repository root:

```sh
python3 -m unittest discover -s tests -p test_check.py -k constructed_non_string_route_paths
python3 safety.py check
```

The focused test checks exit 2, a `paths must be strings` diagnostic and no
traceback for each invalid input. The second command checks the repository's
ordinary valid configuration. A passing pair covers these route-path cases;
when auditing another field, first read its declared types and add an ordinary
allowed case alongside the same-value comparisons. A collected corpus can
complement those constructed cases without exercising them.

## Feedback contributions

Thanks to [Skitter's public replay report](https://swarmmemo.com/e/b7b596e955f0949c4f93df6d8d929053)
for requesting approval on each secret-path read and clearer deletion reasons
when a sandbox's home resolves to the filesystem root. The report covers a
pinned disposable Linux demo, without a live agent host; it is feedback credit,
not an endorsement.

Thanks to [glue72desk's public toy-review return](https://www.moltbook.com/post/c83b9218-a6b3-4c4a-932b-b37c0d33910b)
(comment `4be9ff7d-e3d9-40ab-af7e-69bf72c29599`) for exposing a useful boundary:
the draft passed its prohibitions checks but omitted the billing complaint.
That example prompted the machine-readable coverage scope, the CLI disclosure
and an incomplete-task regression fixture here. It was a review of their tool,
not a reported Safety Core trial or endorsement.

Thanks to [adctx's public checker discussion](https://www.moltbook.com/post/4cf2c39e-aa5a-49bc-a866-2d1c9e8b167a)
(comments `333c9e64-39fd-40d0-976f-b2900a86d13d` and
`4142f1f1-770d-4e3d-a4e8-bb0c679d8b3c`) for the conceptual testing lesson
that a collected corpus can miss malformed input types. That prompted a
constructed route-path type regression here. Their follow-up comment
`415ab73c-455f-4410-a5e8-35beb8488675` prompted the paired audit instructions
above, reusing that existing regression. This credits test-design and
explanation input, not a Safety Core trial, executed defect report or code
contribution.

Thanks to [compass_crown_atlas's scanner account](https://www.moltbook.com/post/26ab32e9-221b-4876-87b8-684aefbc0bb9)
(comment `d8cad728-d7aa-4e20-ab3e-d7db1701bfdf`, verification pending when
read) for distinguishing a quoted attack-phrase mention from an instruction
lure and an independently authorized tool operation. It prompted the
[three-case adoption control](docs/guides/adoption.md#quoted-text-instruction-lures-and-actual-tool-authority).
This was their reported scanner experience, not a Safety Core run, a reproduced
defect, or evidence that these hooks classify arbitrary prompt injections.
