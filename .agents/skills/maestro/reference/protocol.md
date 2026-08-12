# Maestro protocol

The protocol is the semantic boundary between software-change capabilities. It is intentionally smaller than the workflow that uses it.

## Canonical Change Contract

A **Change** is the evolving record of one intended software change and the only lifecycle source of truth.

Before material implementation, the current slice should be represented as a sufficient **Change Contract**:

```text
intent / outcome
+ scope / non-goals
+ relevant repository/domain evidence
+ resolved decisions
+ architecture constraints
+ expected / forbidden delta
+ implementation boundaries
+ proof obligations
+ risk / authority
```

This is semantic state, not a requirement for a long document. PRD fragments, impact maps, plans, verification matrices, and PR descriptions are projections.

A Change contains:

- identity and lifecycle state;
- target identity/fingerprint;
- intent: problem/current state and desired outcome;
- scope: included, excluded, non-goals;
- acceptance claims;
- decisions and unknowns;
- impact: affected surfaces, architecture class, risk, origin/trust;
- authority envelope;
- architecture constraints when material;
- verification obligations;
- execution slices;
- evidence;
- findings;
- residual risk;
- completion state and rationale.

`reference/change.schema.json` defines the interchange shape. The schema is permissive about host-specific metadata but strict about semantic fields that must not be conflated.

## Evidence

Evidence is an observation made against a target in this run.

```yaml
id:
type: read | command | diff | check | human-confirmation | external-reference
source:
target:
observed_at:
claim:
result:
```

Evidence is not a conclusion. A summary may point to evidence but never replace provenance. Negative/completeness claims require an observation capable of falsifying them.

### Validity domain

Evidence belongs to the target it observed. Prefer a target identity/fingerprint precise enough to detect material drift.

When the target changes, invalidate only the evidence whose subject or assumptions changed. Never carry a terminal verification verdict across an unverified target mutation.

## Decision

A Decision is a choice with explicit authority.

```yaml
id:
question:
context:
options:
recommendation:
authority:
status: pending | resolved | rejected | expired
resolution:
blocks:
durability: one-off | reusable | unknown
```

A recommendation is not a resolution. If a pending Decision materially changes dependent work, that work remains blocked.

A resolved reusable Decision should be considered for durable promotion by the capability that owns the relevant concern. This metadata does not itself create a rule or enforcement mechanism.

## Finding

A Finding is a discrepancy between expected and observed state.

```yaml
id:
source:
statement:
evidence:
severity:
disposition: open | fixed | accepted | rejected | deferred
owner:
```

Guardian may use its richer durable finding grammar. Maestro preserves Guardian identity/disposition rather than translating it into a competing taxonomy.

## Authority envelope

Authority is carried by the Change because autonomy is a property of the current action/state, not of an agent identity.

```yaml
authority:
  ceiling: observe | recommend | prepare | execute | commit | merge | deploy
  granted_by:
  basis:
  constraints:
  expires_at:
```

A host may expose tools above the ceiling. Tool availability is not permission.

The ceiling may be derived by a managed system or explicit human authority from risk, reversibility, observability, verification, policy, and context. Open Maestro preserves/enforces the supplied ceiling but does not invent broader permission.

## Acceptance claims and proof obligations

Requirements are claims, not implementation tasks.

```yaml
requirement:
  id:
  claim:
  acceptance:
  criticality:

proof_obligation:
  requirement_id:
  failure_mode:
  observable:
  oracle:
  method:
  evidence_required:
  status: pending | satisfied | failed | not-verifiable
```

A proof obligation is valid only if the proposed observation can distinguish desired behavior from at least one plausible failure. A test that restates implementation logic or can pass while the requirement is false is not a sufficient oracle.

## Architecture class

- `A0` — implementation-local; no architectural meaning, ownership, boundary, public contract, state model, repository-topology rule, or critical property changes.
- `A1` — extends/conforms to an already explicit architectural decision without creating a new material trade-off.
- `A2` — requires a new/revised decision about semantics, state/consistency, ownership, boundaries, public contracts, repository topology/dependency direction, failure behavior, deployment/operation, or critical qualities.

Uncertainty between A1 and A2 is not A1. Inspect until the existing decision is found or route to ARCHER.

## Target identity

A conclusion is about a specific target. Record enough identity to detect material drift: repository/ref, base/head or worktree identity where available, plus affected content/diff fingerprint when the host can provide it.

Evidence and verification receipts are target-bound. If the target changes after evidence is gathered, invalidate affected evidence before terminal success.

## Lifecycle states

Recommended states:

```text
NEW
FRAMING
INSPECTING
NEEDS_DECISION
READY
EXECUTING
VERIFYING
ASSURING
CANDIDATE_READY
NO_CHANGE
BLOCKED
NOT_VERIFIED
INVALID_TARGET
```

Hosts may add non-semantic UI states. They must not weaken these transitions:

- unresolved material Decision -> no dependent execution;
- unresolved A2 -> no architecture-dependent execution;
- insufficient Change Contract/preflight -> no material execution;
- action above authority ceiling -> no execution;
- failed verification -> not candidate-ready;
- target drift -> re-establish affected evidence;
- unaccounted required work -> no terminal success.

## Projections, not parallel truth

The following are views of Change state:

- change brief / PRD fragment = intent + scope + requirements;
- impact map = impact + evidence;
- architecture packet = material architecture constraints/decisions;
- execution plan = slices + dependencies + proof obligations;
- verification matrix = requirements + proof obligations + evidence;
- PR package = intent + actual delta + evidence + residual risk;
- review summary = findings + decisions + evidence.

Do not persist a projection as an independently editable source of truth when the Change already owns the information.

## Pipeline interchange

A pipeline may serialize the Change as JSON and pass it between capabilities. A capability updates only fields it owns and appends evidence/findings rather than rewriting another owner's resolved decision.

The protocol is open and local-first. A future/managed Devanity system may persist and correlate these records, but no semantic field requires a network service or Devanity account.
