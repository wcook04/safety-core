# Foundations and reuse

Primary sources and selected upstream files inspected on 13 October 2026.
These sources inform design choices; their existence does not demonstrate Safety
Core's effectiveness. The runtime and configuration tests establish narrower facts.

## Research that changes the design

| Source | What it informs here | Boundary |
|---|---|---|
| [Claude's Constitution, January 2026](https://www.anthropic.com/constitution); [official versioned source](https://github.com/anthropics/claude-constitution/blob/84fa9a2711837780ffdddf9d9f32820c92f92ede/20260120-constitution.md) | Explain the purpose behind selected rules: oversight, helpfulness, honesty, calibrated claims and correction. | A local rulebook does not replace model training or implement all constitutional values. CC0 source. |
| [Constitutional AI: Harmlessness from AI Feedback](https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback), 2022; [paper](https://arxiv.org/abs/2212.08073) | Make the chosen principles explicit and distinguish them from the mechanism applying them. | The paper describes supervised and reinforcement learning. Safety Core performs neither. |
| [Collective Constitutional AI](https://www.anthropic.com/news/collective-constitutional-ai-aligning-a-language-model-with-public-input), 2023 announcement; [2024 paper](https://arxiv.org/abs/2406.07814) | Treat choosing and revising principles as an explicit governance decision. | Local customization is not equivalent to public deliberation or the paper's training experiment. |
| [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), 2024 | Keep components simple, observable and composable; add complexity only for a demonstrated need. | Architectural guidance, not evidence that this repository improves outcomes. The article notes that its tooling discussion has evolved. |
| [Trustworthy agents in practice](https://www.anthropic.com/research/trustworthy-agents), 2026 | Distinguish the model, harness, tools and environment. Put meaningful oversight at useful boundaries. | Safety Core mainly addresses instructions and selected harness checks; it does not own all four layers. |
| [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), 2026 | Evaluate concrete tasks, trajectories and outcomes, including failures. | A passing configuration check is not an agent-behavior evaluation. |
| [Claude Code hooks reference](https://code.claude.com/docs/en/hooks) | Implement host event inputs and decision outputs. | The host must actually load and invoke the hooks; static configuration is not execution evidence. |

## Existing repositories worth composing with

| Project and inspected revision | Reusable contribution | Relationship to Safety Core |
|---|---|---|
| [GitHub Spec Kit](https://github.com/github/spec-kit/tree/98127c53c8e31b2e28e5ae5e3e7e50ec58cfed78), MIT | Editable constitutions, amendment workflow and governance templates. | Design precedent. Safety Core has no Spec Kit extension manifest or command integration today. |
| [Rulesync](https://github.com/dyoshikawa/rulesync/tree/fac7f7439da167ee4a6fe80b5f5a002d15b2b801), MIT | Generate tool-specific instructions from a shared source; check generation drift. | Optional Rulesync-format export already exists. Additional target generation and host verification are separate operations. |
| [nah](https://github.com/manuelschipper/nah/tree/0a611a824c06dd3c359f42c5f3827ee2088b4298), MIT | Declarative command guards and runtime adapters. | An optional external guard to evaluate; not a bundled dependency or an OS sandbox. |
| [CC Safety Net](https://github.com/kenryu42/cc-safety-net/tree/33e4b00f1d0461386151a708ce2e1d604da80c2d), MIT | Shell-aware command checks and protected configuration paths. | Another external-guard option. Evaluate its exact version, configuration and host integration rather than stacking overlapping blockers by default. |
| [Cupcake](https://github.com/eqtylab/cupcake/tree/27b94b84f6cf555bfde5817deae323ee8cb00cea), Apache-2.0 | Explicit policy evaluation using Rego/Wasm and structured decisions. | A possible backend if executable custom policies become central; its toolchain is beyond the standard-library starter. |

A whole-project fork is not required. Spec Kit supplies a broader development
workflow; Rulesync supplies cross-tool generation; command guards supply different
runtime mechanisms. Safety Core's specific contribution is the inspectable link
between a local rule, its rationale, affected paths, and configured mechanism.
Whether that combination is useful should be tested with people adapting real
repositories, not inferred from an absence of exact competitors.

## Skills worth learning from

- [Anthropic skill-creator](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/skill-creator):
  define triggering situations, keep supporting detail in references, and evaluate
  realistic tasks against a baseline. The skill's own license is Apache-2.0;
  other directories in that repository have different licenses.
- [Rulesync skill](https://github.com/dyoshikawa/rulesync/blob/fac7f7439da167ee4a6fe80b5f5a002d15b2b801/skills/rulesync/SKILL.md):
  import or author shared rules, preview generation, then verify output and drift.
- [Agent Skills specification](https://agentskills.io/specification):
  the portable package format, separate from any particular agent's permissions.

For Safety Core's setup skill, useful evaluation prompts are: adopt into a new
repository; amend a customized rule without overwriting unrelated settings; and
explain a requested policy that has no implemented enforcer. Ordinary bug-fix
prompts should not unexpectedly launch a rulebook rewrite.

## Attribution and claims

Link ideas to their primary sources. If adapting actual template or code text,
retain the upstream notices and license, record the version, and identify local
modifications. A public URL does not make all material freely redistributable.

Use "inspired by" for a design influence, "adapted from" for copied and modified
material, "integrates with" for an exercised interface, and "extension" for an
actual installed extension. None means endorsement or an upstream safety guarantee.

The reference doctrine's existing source entries own its axiom/principle citations.
The [Constitution source notes](../sources/anthropic-constitution/README.md) map
selected ideas to specific local rules. Keep research documents and large PDFs
out of the mandatory agent entry card and runtime dependency path.
