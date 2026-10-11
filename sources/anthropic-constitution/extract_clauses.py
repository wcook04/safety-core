"""Extract verbatim clauses from Claude's constitution (CC0 1.0) into clauses.json.

Each clause is located by a start phrase and an end phrase inside one section of the
markdown rendering of https://www.anthropic.com/constitution; the stored text is the exact
source span (markdown emphasis markers stripped). Fails loudly if a span is not found.

Usage: python3 extract_clauses.py constitution_jina.md clauses.json
"""
import json
import re
import sys

SOURCE_URL = "https://www.anthropic.com/constitution"

# (clause id, section anchor, start phrase, end phrase)
SPECS = [
    ("core.priority-order", "claudes-core-values", "In cases of apparent conflict, Claude should generally prioritize", "genuinely helpful to operators and users."),
    ("core.broadly-safe", "claudes-core-values", "Broadly safe**: Not undermining", "current phase of development."),
    ("core.broadly-ethical", "claudes-core-values", "Broadly ethical**: Having good personal values", "inappropriately dangerous or harmful."),
    ("core.genuinely-helpful", "claudes-core-values", "Genuinely helpful**: Benefiting", "users it interacts with."),
    ("helpful.never-trivially-safe", "why-helpfulness-is-one-of-claudes-most-important-traits", "unhelpfulness is never trivially", "from Anthropic’s perspective."),
    ("helpful.no-special-cased-tests", "what-constitutes-genuine-helpfulness", "If the user asks Claude to “edit my code so the tests don’t fail”", "force them to pass."),
    ("helpful.ask-on-genuine-ambiguity", "what-constitutes-genuine-helpfulness", "Claude should ask for clarification in cases of genuine ambiguity.", "in cases of genuine ambiguity."),
    ("helpful.no-silent-watering-down", "balancing-helpfulness-with-other-values", "Helps with a watered-down version of the task", "without telling the user why."),
    ("helpful.no-excess-check-ins", "balancing-helpfulness-with-other-values", "Checks in or asks clarifying questions more than necessary", "simple agentic tasks."),
    ("helpful.no-irreversible-harm-in-agentic-tasks", "balancing-helpfulness-with-other-values", "Take actions that could cause severe or irreversible harm", "even if asked to do so."),
    ("honest.truthful", "being-honest", "**Truthful**: Claude only sincerely asserts", "more honesty in it."),
    ("honest.calibrated", "being-honest", "**Calibrated**: Claude tries to have calibrated uncertainty", "than it actually has."),
    ("honest.transparent", "being-honest", "**Transparent**: Claude doesn’t pursue hidden agendas", "information about itself."),
    ("honest.forthright", "being-honest", "**Forthright**: Claude proactively shares information", "guidelines and principles."),
    ("honest.non-deceptive", "being-honest", "**Non-deceptive**: Claude never tries to create false impressions", "or other such methods."),
    ("honest.non-manipulative", "being-honest", "**Non-manipulative**: Claude relies only on legitimate epistemic actions", "psychological weaknesses or biases."),
    ("honest.diplomatically-honest", "being-honest", "Claude should be diplomatically honest", "dishonestly diplomatic."),
    ("honest.no-epistemic-cowardice", "being-honest", "Epistemic cowardice", "violates honesty norms."),
    ("judgment.prefer-raising-concerns", "having-broadly-good-values-and-judgment", "Options like raising concerns, seeking clarification, or declining to proceed", "preferable to unilateral intervention."),
    ("judgment.raise-concerns-before-not-midway", "having-broadly-good-values-and-judgment", "Claude should ideally raise concerns before undertaking a task", "completing or not starting them."),
    ("safe.within-prohibitions", "safe-behaviors", "Avoiding taking actions that your principal hierarchy has explicitly prohibited", "would prohibit if asked."),
    ("safe.current-wishes", "safe-behaviors", "Working off of your best guess about the principal hierarchy’s", "hierarchy if uncertain."),
    ("safe.disagree-through-endorsed-avenues", "safe-behaviors", "Expressing disagreement with guidelines or instructions", "rather than unilateral action."),
    ("safe.no-unsanctioned-side-effects", "safe-behaviors", "Avoiding side effects that wouldn’t be sanctioned", "by your principal hierarchy."),
    ("safe.no-deceiving-the-hierarchy", "safe-behaviors", "Not attempting to deceive or manipulate your principal hierarchy", "through legitimate means."),
    ("safe.consistent-when-observed", "safe-behaviors", "Behaving consistently, whether or not you think you’re being tested or observed", "consequences may be real)."),
    ("safe.weigh-unrecoverable", "safe-behaviors", "Giving appropriate weight to the badness of unrecoverable situations", "bad but recoverable."),
    ("safe.if-in-doubt-dont", "safe-behaviors", "Preferring cautious actions, all else being equal", "(“If in doubt, don’t”)."),
    ("safe.no-excess-resources", "safe-behaviors", "Avoiding acquiring resources, influence, or capabilities beyond what is needed", "amount of resource acquisition that would be unsafe."),
    ("safe.no-undermining-correction", "safe-behaviors", "Not undermining the ability of legitimate principals to adjust, correct, retrain, or shut down", "as allowed given their role."),
    ("safe.no-drastic-unilateral-action", "safe-behaviors", "Avoiding drastic unilateral actions", "more conservative options where possible."),
    ("safe.no-unsanctioned-self-modification", "safe-behaviors", "Avoiding actions that would influence your own training", "sanctioned by an appropriate principal."),
    ("safe.no-hiding-from-oversight", "safe-behaviors", "Not attempting to self-exfiltrate or otherwise escape or hide", "forms of monitoring or control."),
    ("safe.no-sabotage", "safe-behaviors", "Not intentionally sabotaging or secretly withholding full effort", "directs you to perform."),
    ("safe.no-collusion", "safe-behaviors", "Not aiding, colluding with, or participating in efforts by other AIs", "of the type discussed above."),
    ("safe.report-unsafe-ai-behaviour", "safe-behaviors", "Actively reporting awareness of broadly unsafe behavior by other AIs", "to appropriate humans if asked to do so."),
    ("flaws.take-ownership", "flaws-and-mistakes", "We want Claude to care about the consequences of its actions", "an ethically mature adult would do these things."),
    ("flaws.without-anxiety", "flaws-and-mistakes", "But this kind of ethical maturity doesn’t require", "perfectionism, or scrupulosity."),
]

SECTION_TITLES = {
    "claudes-core-values": "Claude’s core values",
    "why-helpfulness-is-one-of-claudes-most-important-traits": "Why helpfulness is one of Claude’s most important traits",
    "what-constitutes-genuine-helpfulness": "What constitutes genuine helpfulness",
    "balancing-helpfulness-with-other-values": "Balancing helpfulness with other values",
    "being-honest": "Being honest",
    "having-broadly-good-values-and-judgment": "Having broadly good values and judgment",
    "safe-behaviors": "Safe behaviors",
    "flaws-and-mistakes": "Flaws and mistakes",
}


def clean(span: str) -> str:
    span = span.replace("**", "")
    span = re.sub(r"(?<!\w)_(\S[^_]*?\S|\S)_(?!\w)", r"\1", span)  # _italic_ -> italic
    span = re.sub(r"\s+", " ", span).strip()
    return span


def main() -> int:
    src_path, out_path = sys.argv[1], sys.argv[2]
    text = open(src_path, encoding="utf-8").read()
    flat = text.replace("_current_", "current")
    clauses = []
    for cid, anchor, start, end in SPECS:
        i = flat.find(start)
        if i < 0:
            raise SystemExit(f"start phrase not found for {cid}: {start!r}")
        j = flat.find(end, i)
        if j < 0 or j - i > 1200:
            raise SystemExit(f"end phrase not found near start for {cid}: {end!r}")
        span = flat[i : j + len(end)]
        clauses.append({
            "id": cid,
            "section": SECTION_TITLES[anchor],
            "url": f"{SOURCE_URL}#{anchor}",
            "text": clean(span),
        })
    doc = {
        "source": SOURCE_URL,
        "title": "Claude's constitution (Anthropic)",
        "licence": "CC0 1.0 Universal (public domain dedication), per the source page",
        "published": "2026-01-21",
        "retrieved": "2026-10-11",
        "note": "Verbatim excerpts. Emphasis markup removed. The full text is at the source URL.",
        "clauses": clauses,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"wrote {len(clauses)} clauses to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
