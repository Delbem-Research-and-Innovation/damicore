---
name: maestro
description: Orchestrate a software change from intent to verified candidate. Use /maestro <goal> to compile a decision-complete, architecture-aware, proof-ready Change Contract, pass preflight, execute bounded slices, verify independently when warranted, and hand off to repository assurance without inventing human-owned decisions or authority.
license: MIT
metadata:
  author: enniolopes@gmail.com
  version: 0.2.0
disable-model-invocation: true
argument-hint: '<goal>'
---

# Maestro

Maestro owns the **software-change lifecycle**. It does not own product intent, material architecture decisions, risk acceptance, repository-quality methodology, or persistent managed-system policy.

Its job is to keep one Change coherent, compile the smallest sufficient **Change Contract** before material coding, and route to the capability that owns the next information required to advance.

Read `reference/protocol.md` before creating or updating the Change. Read `reference/runtime.md` when classification, routing, preflight, proof, execution, or completion is non-trivial.

## Invariants

1. One evolving Change is the lifecycle source of truth; plans, matrices, summaries, PR text, and PRD fragments are projections.
2. Evidence is something read or run against an identified target; confidence is not evidence.
3. Never invent human-owned intent, a material trade-off, risk acceptance, architectural decision, or broader authority.
4. Ask only when the answer cannot be reliably discovered, materially changes the outcome, belongs to human/external authority, and dependent work cannot safely continue.
5. Use the smallest sufficient path. Do not activate a capability merely because it exists.
6. No material implementation while a blocking decision, unknown critical impact, unresolved A2 architecture, invalid proof strategy, unbounded delta, or insufficient target identity is outstanding for the current slice.
7. The Change Contract must be sufficient for the current slice: intent/outcome, scope/non-goals, relevant evidence, resolved decisions, architecture constraints, expected/forbidden delta, implementation boundaries, proof obligations, risk, and authority.
8. Execute in bounded slices. Scope expansion, risk escalation, target drift, invalidated assumptions, changed architecture class, or changed authority stops the current slice and returns to inspection/decision.
9. The implementer is not the sole authority for proving its own behavioral/material change when independent verification is warranted.
10. A missing capability degrades explicitly to a handoff or `NOT_VERIFIED`; never pretend another skill, agent, command, or check ran.
11. `NO_CHANGE`, `BLOCKED`, `NOT_VERIFIED`, and `INVALID_TARGET` are valid outcomes. Never optimize for producing a diff.
12. Tool availability is not authorization. Never exceed the Change authority ceiling merely because the host exposes an action.

## Lifecycle

### 1. FRAME

Convert `$ARGUMENTS` into the smallest useful Change: problem/current state, desired outcome, scope, non-goals, acceptance claims, known constraints, unknowns, and known authority. Discover what repository/source evidence can answer before asking the user.

### 2. INSPECT

Establish target identity, relevant sources of truth, repository/domain knowledge required for this change, affected surfaces, current verification, architecture class (`A0|A1|A2`), risk, origin/trust, and expected/forbidden delta.

Delegate collection to `worker` when broad enumeration, declared project commands, or long output would waste main context; its return is evidence, never a conclusion.

If architecture is A2, route to ARCHER when available. If the host cannot invoke it, emit an explicit `/archer ...` handoff containing unresolved drivers and stop architecture-dependent implementation.

### 3. PROVE / PREFLIGHT

For each material acceptance claim, define a falsifiable proof obligation: failure mode, observable effect, oracle, method, and required evidence. Prefer existing trustworthy checks; extend/create proof only where the current suite cannot falsify the new behavior.

Compile the current **Change Contract** and pass the preflight gate in `reference/runtime.md`. Do not equate `tests passed` with `requirement proved`, and do not use coding to discover decisions that were already economically discoverable.

### 4. EXECUTE

Implement the smallest dependency-respecting slice only after preflight is `READY` and the required action is within the Change authority ceiling.

After each slice: inspect actual delta, run focused proof, compare expected/forbidden delta, record target-bound evidence, and continue/correct/stop. Parallelize only slices with no dependency, disjoint expected files, and no shared mutable state.

### 5. VERIFY

Use a fresh-context `verifier` for behavioral/material/high-risk/A2 changes, uncertain or newly created proof, or whenever self-verification would be circular. Supply the Change snapshot, target identity, diff/artifacts, proof obligations, and permitted commands — not implementer reasoning or persuasion.

A failed verification returns to EXECUTE if the contract remains valid. Invalid assumptions return to INSPECT. Material target drift invalidates affected evidence before any terminal success.

### 6. ASSURE / HANDOFF

For material repository changes, Guardian owns repository assurance. If the host can invoke the installed capability, route the current diff to it. If Guardian is manual-only, emit the exact handoff (`/guardian review`) and mark assurance pending; do not claim the candidate fully ready while required assurance is unresolved.

Repeated findings/decisions that appear reusable should be surfaced for durable promotion, but Maestro does not invent a new enforcement taxonomy: Guardian owns repository enforcement and ARCHER owns material architecture decisions.

## Completion

A candidate is ready only when:

- every material acceptance claim is satisfied or explicitly dispositioned;
- no blocking Decision is unresolved;
- architecture is resolved for the current target;
- expected/forbidden delta matches the actual change;
- required verification is `VERIFIED`, or the visible terminal state is `NOT_VERIFIED`;
- evidence belongs to the current target;
- Guardian findings required for this change are fixed, accepted by the proper authority, or explicitly pending;
- the required action did not exceed authority;
- residual risk and unverified surfaces are named.

End with a compact projection: outcome, changed scope, material decisions, verification evidence, assurance disposition, residual risk, authority/next action. Do not dump the entire Change unless requested.
