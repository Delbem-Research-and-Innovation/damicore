# ARCHER method

ARCHER is a six-phase architecture method. The phases are ordered by dependency, not ceremony. Skip depth that cannot affect a decision; never skip an unresolved class of information that a later decision depends on.

## P1 — Align

**Question:** What must be true, for whom, and why?

Owns:

- system/change purpose and boundary;
- stakeholders and decision authority;
- capabilities and non-goals;
- architectural drivers;
- critical properties and hard constraints;
- quality scenarios;
- dominant losses/risks;
- relevant scale/evolution horizon.

Does not own detailed domain state, component decomposition, protocols, or concrete enforcement.

For an abstract quality, derive an observable scenario:

```yaml
property:
source:
stimulus:
environment:
affected_artifact:
expected_response:
measure:
criticality:
owner:
```

**Gate:** no critical driver is undispositioned; purpose, boundary, non-goals, authority, and critical properties are explicit enough to constrain later choices.

## P2 — Represent

**Question:** What does the system mean and how may its state change?

Owns:

- concepts and vocabulary;
- identity;
- state and transitions;
- invariants;
- commands/events where relevant;
- units of consistency;
- sources of truth;
- semantic ownership;
- assumptions and validity conditions.

For each important concept:

```yaml
concept:
meaning:
identity:
owned_state:
invariants:
commands:
events:
source_of_truth:
semantic_owner:
```

For a transition:

```text
current state + command + preconditions
-> new state + effects + events
```

State what an event or status **does not mean** when conflation would create defects. Example: authorization is not settlement; accepted request is not completed outcome.

Track epistemic status for material claims when useful: proposed, accepted, implemented, mechanically-enforced, operationally-observed, disputed, stale, invalidated, superseded. Evidence may be observed, derived, inferred, human-confirmed, or mechanically-enforced.

**Gate:** central concepts have stable meaning; invariants and transitions are explicit; source-of-truth and semantic ownership are known; later boundaries will not be asked to repair semantic ambiguity.

## P3 — Compose

**Question:** Where do state and responsibility reside and how do units collaborate?

Owns:

- architectural boundaries;
- responsibility and state ownership;
- dependency direction;
- public/internal contracts;
- synchronization/coordination choices;
- data ownership and replication boundaries;
- interfaces between independently changeable units.

Derive boundaries from reasons to change, consistency needs, failure containment, security/trust, scaling independence, and ownership — not from nouns or framework conventions.

For each unit:

```yaml
unit:
responsibility:
owned_concepts:
owned_state:
public_contracts:
dependencies:
forbidden_dependencies:
local_invariants:
local_verification:
owner:
```

A boundary is justified only if it creates a useful independence or control surface. A module/service with no independent responsibility, contract, state, failure boundary, ownership, or evolution need is likely an empty axis.

Prefer one source of truth per meaning. Replication must have an explicit authority and reconciliation rule.

**Gate:** every important responsibility/state has one clear owner; collaboration occurs through explicit contracts; dependency direction supports the required independent changes; no boundary exists only because a pattern suggested it.

## P4 — Harden

**Question:** How must the design behave under failure, pressure, misuse, and attack?

Owns:

- failure modes and containment;
- timeout/retry/idempotency semantics;
- concurrency and consistency failure behavior;
- overload/backpressure/degradation;
- security/trust boundaries;
- privacy and destructive-operation controls;
- recovery/rollback/reconciliation;
- audit/evidence requirements;
- operational hazards.

Stress the design with scenarios rather than labels:

```yaml
hazard:
trigger:
path_to_loss:
preventive_controls:
detection:
containment:
recovery:
residual_risk:
authority_to_accept:
```

Important distinctions:

- retryability is not idempotency;
- "at least once" delivery requires consumers/actions that tolerate duplicates or reconcile them;
- authorization is separate from decision and execution;
- an attempted action is not an observed outcome;
- observability is not correctness, but undetectable critical failure is an architectural defect;
- human confirmation records authority/risk acceptance; it does not provide technical isolation.

**Gate:** critical losses have prevention/detection/containment/recovery dispositions proportional to risk; nominal-path architecture is not presented as complete.

## P5 — Encode

**Question:** How do decisions become executable, observable, and verifiable?

Owns:

- types and schemas;
- contract tests and dependency rules;
- static checks and fitness functions;
- CI/runtime policy gates;
- observability signals tied to properties;
- verification commands;
- decision records and machine-readable constraints where valuable.

Use the strongest mechanism that can decide the property with acceptable precision and latency. Documentation explains meaning; it should not be the only control for a mechanically decidable critical invariant.

For each critical property:

```yaml
property:
architecture_decision:
enforcement:
verification:
operational_signal:
evidence_owner:
known_blind_spots:
```

Do not invent a universal "architecture health" score. Evidence is property-specific. A passing check proves only the property and target it can actually falsify.

**Gate:** every critical decision has either durable enforcement/evidence or an explicit reason why it remains human-judged; implementation can discover the relevant rule with bounded context.

## P6 — Release and Revise

**Question:** What did reality validate, invalidate, or make worth revisiting?

Owns:

- implementation/conformance review;
- operational evidence against assumptions;
- architecture decision revision triggers;
- supersession/deprecation of decisions;
- learning promoted into stronger contracts/enforcement;
- accepted residual risk and follow-up conditions.

A decision record is not a monument. Revisit when an assumption becomes false, a quality scenario misses its bound, operational evidence contradicts the model, change amplification grows materially, a boundary repeatedly leaks, or a simpler architecture now spans the observed problem.

**Gate:** the implemented system is traceable back to critical decisions, significant deviations are explicit, and every still-conditioned decision has a visible revision condition.

## Cross-phase decision record

For every material decision:

```yaml
id:
context:
drivers:
alternatives:
decision:
properties_favored:
properties_sacrificed:
consequences:
assumptions:
enforcement:
evidence_expected:
revise_when:
authority:
status:
```

Do not manufacture alternatives after deciding. If there was one forced solution, state the constraint that forced it.

## Basis-form check

Use four tests on the architecture itself:

- **Irreducible** — no duplicate semantic owners, rules, schemas, state authorities, or parallel truth that can drift independently.
- **Orthogonal** — concerns change for one reason; independent decisions are not entangled without necessity.
- **Spanning** — the model covers relevant states, failure modes, constraints, and change classes rather than enumerating only current examples.
- **Decodable** — a human or agent can locate meaning, ownership, contracts, invariants, and local verification with bounded context.

Do not turn these into a scalar. A design may improve one axis while worsening another; material trades require explicit authority.

## Derivation order for novel problems

When the method does not spell out a particular architecture:

```text
1. Name the outcome or loss that matters.
2. Translate it into a property/scenario/constraint.
3. Identify the semantic/state invariant behind it.
4. Assign one owner/source of truth.
5. Choose the smallest boundary/contract that preserves it.
6. Stress that choice under failure, pressure, and threat.
7. Encode the important rule as a check/control when feasible.
8. State the evidence that could falsify the decision.
9. Record assumptions and the condition that would make revision rational.
```

A solution is not justified by popularity, novelty, or pattern vocabulary. The justification is the trace from property to decision to evidence.

## Avoid

- technology-first architecture;
- microservices/modularity as goals by themselves;
- introducing abstractions for hypothetical consumers;
- using asynchronous/event-driven designs without failure/ordering/idempotency semantics;
- conflating logical ownership with physical deployment;
- duplicating domain meaning between code, schemas, docs, and prompts without one authority;
- assuming eventual consistency is acceptable without a business/state invariant;
- architecture documents whose decisions cannot be found in implementation or enforcement;
- high-level diagrams with no state, failure, or contract semantics;
- claiming scalability, security, reliability, or AI-operability without observable scenarios.

## Minimality test

For each proposed architectural element ask:

1. Which concrete driver/property requires it?
2. Which failure/change class becomes easier to contain or reason about because it exists?
3. What new cost/control surface does it introduce?
4. Could a smaller structure satisfy the same properties?

If no driver survives those questions, remove the element.
