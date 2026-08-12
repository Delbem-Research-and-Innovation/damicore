# Guardian — Enforcement promotion

## Promotion path (the ratchet)

Promote by class and by observable evidence — never by a remembered count you cannot verify.

- Any mechanizable finding → propose codification now (test/type/schema/lint).
- The high-risk class → propose deterministic enforcement immediately (lint/typecheck/test/CI/hook).
- Observable repetition (the same issue across several files in this diff, a prior finding in this conversation, or an existing issue/TODO) → strengthen from a suggestion to a durable gate, and cite the evidence.
- Do not assert a recurrence count you cannot point to.
- Promotion is a **move, not a copy**: after codifying, demote the source prose to a pointer at the check — rationale the check can't express may stay; the rule itself is never restated. The demotion belongs to the same approved unit, not a second finding. Enforcement plus parallel prose is the duplication the promotion was meant to end.

## Enforcement type by target

Two independent choices — **what kind of check** the rule needs, and **where it fires**. Conflating them is how a rule that a configured lint could decide in the editor ends up as a CI job instead.

```txt
static rule       → lint / typecheck
behavior          → test
domain contract   → spec + test
```

## Trigger — the latency axis of the `enforcement` rung

Two mechanisms on the same rung can differ by orders of magnitude in feedback latency, and a loop's stability tracks that latency. So the rung alone does not finish the decision: within `enforcement` (`SKILL.md` ladder), pick the **innermost trigger that can decide the rule**. A check that only runs at PR when a configured lint could have decided it in the editor leaves the agent iterating open-loop until the PR — every wrong step in between is a step it took believing it was fine.

```txt
editor / on save             type, schema, a lint rule already configured   ← innermost, prefer
before an action / on stop   platform hooks (see bindings.md)
pre-commit / pre-push        fast focused check, formatter, targeted lint
at PR / merge                CI: full suite, coverage gate, cross-package check
runtime                      assertion, invariant check, alert              ← outermost, slowest signal
```

Innermost is a preference, not a mandate: a rule that needs the whole repo (cross-package boundary, coverage across the suite) cannot decide in the editor, and forcing it inward buys latency with false positives. Moving inward also moves cost onto every keystroke or commit — so the trigger chosen is named in the fix's `basis:` alongside that cost, exactly like any other enforcement cost (`SKILL.md` Fix classification).

## Syndrome → check

The syndrome→check mapping is the last column of the canonical crosswalk in `basis-form.md` — use it there; it is not restated here.

## Before codifying a prose rule, confirm

- precise enough to enforce mechanically;
- low false-positive rate;
- doesn't encode product intent a human must approve first;
- won't block legitimate future work.

If any fails, keep it as guidance and record why — not every good guideline makes a good check. If enforcement needs a **new dependency** or a **hook/CI change**, stop and propose it (respect any "no new dependencies" rule).
