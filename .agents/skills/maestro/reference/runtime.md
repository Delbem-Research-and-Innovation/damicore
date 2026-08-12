# Maestro runtime

This file turns the Change protocol into execution decisions. The goal is proportional rigor: the cheapest path that can still justify the conclusion.

## 1. Frame before implementation

Start from the user's goal, then discover repository/source evidence before asking questions.

Minimum useful frame:

```yaml
problem:
desired_outcome:
scope:
  included:
  excluded:
non_goals:
acceptance_claims:
constraints:
unknowns:
authority:
  ceiling:
```

A request phrased as a solution is evidence of intent, not permission to invent the problem it supposedly solves. Preserve explicit user choices; surface material ambiguity.

## 2. Compile context, do not dump context

The best implementation context is the smallest context that preserves every material constraint.

Before coding, assemble only what the Change needs from:

```text
intent
repository truth
architecture
resolved decisions
repository/domain rules
verification knowledge
```

Do not load unrelated repository history merely because it is available. Good repository topology, scoped instructions, explicit contracts, and source-of-truth references should reduce search and inference.

Stable repository knowledge should not be recopied into every Change Contract; reference the authoritative source and include only the change-specific implication.

## 3. Independent classification axes

Do not compress these into one "complexity" score.

### Behavior

- `trivial` — typo/comment/format or localized non-behavioral edit; no contract, verification, ambiguity, instruction-surface, or topology change.
- `behavioral` — observable behavior, state, contract, data shape, error behavior, or operational behavior changes.

### Architecture

Use A0/A1/A2 from `reference/protocol.md`.

Repository topology is architectural when placement, ownership, public surface, or dependency direction changes materially. Creating a folder by itself is not A2; changing the system's semantic decomposition is.

### Risk

Treat a change as high-risk when a violation can be irreversible, silent, or defeat detection itself: security/auth/permissions/privacy, payments/billing, destructive data/migrations, public compatibility contracts, critical infrastructure, audit/evidence/provenance, or a novel case with the same failure property.

Membership depends on behavior/contract altered, not merely the directory touched.

### Verification

- `sufficient` — a trustworthy existing oracle can falsify the material new behavior.
- `missing` — no relevant oracle exists.
- `uncertain` — an oracle exists but may be circular, low-fidelity, flaky, incomplete, or mismatched to the requirement.

### Origin / execution trust

- `trusted-local` — current local work the user intentionally operates on.
- `external` — fetched PR/patch/branch or other explicitly external code.
- `unknown` — provenance is not established.

Reading content is not executing it. Before executing external/unknown project code, require a real sandbox or explicit human acceptance of the exposure; consent is not isolation.

## 4. Investigation and Worker

Use main context for small, decision-relevant reads. Delegate to Worker when the deliverable is collection rather than judgment:

- broad occurrence enumeration;
- long logs/test/lint/build output;
- environment/service/container state;
- repository-declared command execution;
- large but mechanical inventories.

A Worker result is evidence. Maestro interprets it. `NOT RUN` is valid and must not be rewritten as a successful check.

Do not delegate a one-line read just to use an agent.

## 5. Architecture routing

A0: proceed without ARCHER; record why no material architecture property changes.

A1: cite the existing decision/boundary/contract being followed. If that reference cannot be found, do not claim conformance by intuition.

A2: supply ARCHER with:

```yaml
purpose:
current_semantics:
drivers:
critical_properties:
constraints:
affected_state_and_boundaries:
repository_topology_implications:
known_options:
unknowns:
required_decisions:
```

ARCHER returns architecture constraints/decisions; Maestro owns sequencing afterward. Architecture work is complete only when implementation can tell what must remain true, where responsibility belongs, what dependencies are allowed, and how critical properties will be checked.

## 6. Human-question gate

Ask only when all are true:

1. repository/source evidence cannot reliably resolve the answer;
2. different answers materially change product behavior, architecture, risk, scope, or authority;
3. the decision belongs to the human or another external authority;
4. dependent work cannot safely continue under a bounded assumption.

Otherwise discover, infer with an explicit non-blocking assumption, or continue on unaffected work.

A decision request should contain the rule-level question, context, realistic options and durable consequences, a labeled recommendation when evidence supports one, authority, and what remains blocked if unanswered.

## 7. Change Contract and preflight gate

Implementation is `READY` only when the current slice has a sufficient Change Contract:

- intent and acceptance claims are sufficient;
- impacted sources of truth and boundaries are known to required depth;
- relevant stable repository/domain knowledge has been located rather than reinvented;
- architecture is A0/A1 with evidence or A2 resolved;
- high-risk membership is known;
- no blocking human/external Decision remains;
- expected and forbidden delta are bounded;
- implementation placement/ownership is clear enough to avoid architectural guessing;
- a proof strategy exists for every material claim;
- target identity is sufficient to detect relevant drift;
- the required action is within the supplied authority ceiling.

Failure modes:

- `false-ready` — implementation later needs a material product/architecture decision, major scope expansion, placement redesign, or proof redesign that should have been visible before code;
- `false-block` — investigation demands information that cannot affect the current safe slice.

Optimize both, not only caution.

Do not require a perfect whole-system spec before every local change. Preflight is slice-scoped and proportional.

## 8. Verification design

For each material requirement derive:

```text
claim
-> plausible failure mode
-> observable consequence
-> oracle
-> method
-> evidence
```

Prefer the cheapest reliable method:

- types/schema/static rules for structural properties;
- focused unit/contract/integration tests for deterministic examples;
- property-based testing for broad input domains with meaningful invariants;
- state-machine/model-based testing for transition systems;
- metamorphic/differential testing where the expected relation is clearer than exact output;
- selective mutation testing to challenge whether an important test can detect plausible implementation faults;
- live/preview/runtime verification when local substitutes cannot falsify the real integration behavior;
- manual observation only when automation is not proportional or the property is inherently experiential.

Property-based testing is not a default. Use it when a property is authoritative enough and domain exploration adds information beyond hand-picked cases. An inferred property cannot become blocking merely because an LLM proposed it.

A newly written oracle should, when practical, be observed failing against the actual defect or a deliberate reversible violation before the implementation correction is allowed to prove it. If no reachable falsification exists, state that limitation.

## 9. Authority gate

The Change authority envelope may specify a maximum action:

```text
observe < recommend < prepare < execute < commit < merge < deploy
```

Before a side effect:

1. identify the action class;
2. compare it with the current ceiling;
3. check any constraints/expiry;
4. stop at `NEEDS_DECISION`/handoff if broader authority is required.

Tool availability, repository permission, or model confidence never expands authority.

## 10. Slice design

A slice is the smallest unit that can be implemented and meaningfully checked.

Record:

```yaml
id:
depends_on:
expected_files:
expected_delta:
forbidden_delta:
proof_obligations:
status:
```

After each slice:

```text
implement
-> inspect actual delta
-> run focused proof
-> compare expected/forbidden delta
-> bind evidence to current target
-> continue | correct | stop
```

Parallel execution is allowed only when all are true:

- no dependency edge between slices;
- expected file sets are disjoint;
- no shared mutable state or migration/order coupling;
- each slice has an independent verification boundary.

"Multiple agents are available" is not a reason to parallelize.

## 11. Stop and re-route

Stop the active slice when any occurs:

- target changed materially;
- scope expanded beyond the approved boundary;
- an assumption was invalidated;
- a new human-owned decision appeared;
- architecture class rose to A2 or an A2 decision changed;
- repository placement/ownership is no longer clear;
- risk class increased;
- authority ceiling is insufficient for the next action;
- proof strategy became invalid or circular;
- verification produced unexplained side effects.

Return to INSPECTING or NEEDS_DECISION; do not push through uncertainty.

## 12. Independent verifier brief

Use the installed `verifier` agent when present. Otherwise a genuinely fresh-context, no-write subagent may perform the same contract, with weaker enforcement stated.

Supply only:

```yaml
change_snapshot:
target_identity:
diff_or_artifacts:
acceptance_claims:
proof_obligations:
permitted_commands:
execution_trust:
```

Do not supply implementer chain of reasoning, persuasive narrative, or a claim that the change is already correct.

Verifier outcomes:

- `VERIFIED` — required claims have sufficient evidence on the current target;
- `FAILED` — observed evidence contradicts one or more claims;
- `NOT VERIFIED` — required evidence could not safely or adequately be obtained;
- `INVALID TARGET` — target drift makes supplied evidence non-reconcilable.

FAILED returns to EXECUTE if the contract remains valid. Invalid assumptions return to INSPECT.

## 13. Guardian assurance and durable promotion

Guardian is not a second general verifier. It owns repository quality: basis-form, durable enforcement, topology/boundary drift, instruction surfaces, recurring findings, and risk-aware review.

Maestro may use Guardian's result but does not reinterpret its severity/fix-class taxonomy. If the host requires manual invocation, the lifecycle remains `ASSURING` and the visible next action is `/guardian review`.

Do not force deep Guardian analysis for a truly trivial fast-path change when Guardian's own contract says the fast path applies.

When a resolved Decision or Finding appears reusable, flag it for the relevant owner to consider durable promotion. Prefer stronger representations—types, schemas, static rules, tests, CI/policy—before adding permanent prose when the property is mechanically decidable.

## 14. Legacy/weak repositories

Do not require a repository to become ideal before a bounded change can ship.

If tests, topology, boundaries, or instructions are weak:

- state reduced assurance explicitly;
- introduce the smallest regression harness needed for current behavior when proportional;
- constrain scope more tightly;
- preserve unknown residual integration risk;
- let Guardian surface structural improvement separately.

"Repository quality is weak" is context, not an automatic block.

## 15. No-change and abort

If evidence shows the requested behavior already holds, the reported defect is outside the repository, or the proposed change would violate authoritative intent, return `NO_CHANGE` with evidence and rationale.

If safe progress depends on unavailable authority/evidence, return `BLOCKED` or `NOT_VERIFIED`. These are correct outcomes, not productivity failures.

## 16. Final projection

Do not dump internal orchestration state by default. Report:

```text
Outcome
What changed / no-change reason
Material decisions
Verification performed and result
Guardian/assurance disposition
Residual risk or not-verified surfaces
Authority / next human action
```

A PR description is derived from the same Change and actual diff; never copy planned checks as if they were executed.
