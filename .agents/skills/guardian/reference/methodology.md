# Guardian — Methodology reference

## AI Repo dimensions

The dimensions numbered below are the single operational lens, and this list is their one home — every finding carries exactly one of these slugs (a basis-form test name is never a finding tag). Never restate how many there are: the count is derivable from this list, so a call site that states it goes stale the moment a dimension is added or removed (the source repo's CI checks this). Each dimension's parent test and promotion check live in the canonical crosswalk in `basis-form.md`; the bad-lists below are the operational detail. Relevance rule: a dimension is relevant iff the diff/scope touches an artifact it governs; when unsure, check it. **Sufficiency rule**: a relevant dimension counts as *checked* only when the evidence its parent test requires (the crosswalk's evidence column, `basis-form.md`) was read this run and is cited — that evidence usually lies outside the change. Gather it in proportion to blast radius, or record the dimension as **not checked** with the reason — not relevant · evidence unavailable · evidence disproportionate to this change's blast radius — never as checked. Under an exhaustive contract, a dimension left unevidenced for capacity is not a disposition but pending completion (`modes/audit.md`). When a small change needs a large evidence set to judge it, that is itself a `compressibility` observation. Trace an emission or write to its **sink**, not its call-site's apparent domain — a metrics/log call that also writes to an audit/evidence/provenance record, ledger, or other high-risk-class sink is governed by that sink's dimensions and class membership, not by the call site's surface label (e.g. "telemetry"). Skipping is a decision, never silent — `audit` dispositions a dimension it cannot evidence as an `UNKNOWN` row (a dimension skipped for capacity is completion pending instead, `modes/audit.md`); `review` records every dimension under Coverage, checked with its cited evidence or not checked with its reason. Never flag what the baseline shows already enforced.

**Axis-cited classification.** A dimension tag is valid only when the finding's evidence actually maps to its parent crosswalk test (`basis-form.md`) — never when it is chosen by pattern-matching the call site's surface vocabulary (a variable, function, or event name). The mapping is carried by the `why:`'s framing, not by naming the test in every finding (`reference/format.md` — the field is framed by the axis, and the test name is never a finding tag); what must hold is that the test **can** be named on demand. If a finding can't name its test when asked, it isn't classified yet — re-trace it to its sink or contract before tagging. Before finalizing severity/dimension, run the swap-test: would this classification survive if the surface label were replaced by a neutral placeholder, holding the underlying contract fixed? If the answer changes when the label does, the surface was classified, not the essence. The swap-test is never rendered as its own paragraph — a "root cause:" section that doesn't change any tag is decoration, not diagnosis. Its only legitimate trace is a severity or dimension that comes out differently than naive pattern-matching would have produced; judge this discipline the way Guardian judges itself — not by how often the test is mentioned, but by how often it changes a call.

1. **Context compressibility** (`compressibility`) — can the change be explained through a small, bounded context packet? Bad: small behavior needs whole-system understanding; logic spread across layers; new cross-cutting knowledge with no contract; a large file becoming a gravity well.
2. **Executable specification** (`executable-spec`) — is important intent in tests, types, schemas, validators, or specs (not just conversation)? Bad: new behavior without acceptance tests; business rule hidden in a conditional; requirement only in an issue comment; spec duplicating code-readable facts instead of intent/boundaries/non-goals.
3. **Co-located specs** (`co-located-spec`) — when code can't express intent, use `*.spec.md` beside the artifact. Good: intent, constraints, acceptance criteria, boundaries, non-goals, risk class, verification commands. Bad: rewritten source, duplicated type shapes, generic prose, untested assertions. Doc-comment/docstring claims belong here (code-adjacent spec, incl. the JSDoc policy below), never to `instruction-hygiene` — that dimension governs agent-loaded instruction surfaces only.
4. **Verification loop** (`verification-loop`) — two axes, both required: **cost** (can a future agent run a focused check quickly?) and **oracle fidelity** (can the check actually fail when the contract breaks?). Bad, cost: only manual testing proves it; only slow e2e covers local behavior; command not discoverable; PR claims success without evidence. Bad, fidelity: snapshots updated without reviewing the diff; asserting status/shape where the contract is the payload; behavior at a deployed boundary (live schema, persisted data) covered only by mocks.
5. **Boundary integrity** (`boundary-integrity`) — are package/layer/domain/ownership/public-API boundaries preserved **and enforced**? Check both: does the change violate a boundary, and does the boundary exist only in prose (candidate for import-restriction lint / dependency-graph check)?
6. **Pattern hygiene** (`pattern-hygiene`) — did the change copy or strengthen a bad local pattern (more nesting in a complex fn, more special cases in a god file, a workaround becoming the norm, "file style" that is actually debt)? Agents replicate whatever they see. Greenfield code has no local pattern to copy — it seeds one: judge a new package/module as the convention future agents will replicate, never skip this dimension as irrelevant just because the code is new.
7. **Debt containment** (`debt-containment`) — accept debt only if modular, visible, observable, cheap to repay. Unacceptable: invisible, systemic, untested, in core logic, or likely to be copied.
8. **Instruction & context hygiene** (`instruction-hygiene`) — review the instruction surfaces in scope (from the baseline) with the syndromes below. Also bad: CLAUDE.md grown into a manual (target <200 lines); generic advice; local rule placed globally; procedure that belongs in a skill; the same rule hand-duplicated across tools, or — when in-repo evidence shows it — across the org's repos (drift; the same irreducible violation one level up: flag a shared-surface candidate, don't create it). Loading/precedence mechanics live in `bindings.md`.

## Instruction-artifact syndromes

Apply to every instruction surface in scope — CLAUDE.md/rules/AGENTS.md-class files **and agent skill files**. Mechanical, one pass per surface; every hit cites file + quoted line:

1. **Undefined term** — every term used operationally in ≥2 places has exactly one definition site.
2. **Claim diff** — a fact stated in more than one file must agree in substance everywhere; diff the statements.
3. **Quantifier audit** — for every `always/never/only/all/once/"X does Y"` claim, verify it holds against each mode/scope/constraint it spans (the JSDoc never/always rule below, applied to instructions).
4. **Classification totality** — push boundary cases through every rule table (severity, routing, verdicts): exactly one bucket may fire; two or zero → finding.
5. **Template drift** — every output template and worked example must carry every mandatory field of the format it instantiates; prose and template must agree on cardinality.
6. **As-rendered** — evaluate the file as the runtime renders it: substitute placeholders (e.g. `$ARGUMENTS`) literally, under empty / one / many tokens (mechanics in `bindings.md`).
7. **Unsupplied precondition** — for every requirement an instruction places on its reader (data to check against, a capability to use, an artifact to write into), the source must be reachable by the actor that must satisfy it, at the moment it must. Three ways it fails, each a hit: the source sits in another **distribution unit** (a check that ships elsewhere than the surface claiming it), outside the actor's **load-set** (a list a mode must validate against but its row does not load), or is merely **assumed present in the target repo** (a tracker, hook, or command the repo may not have, with no branch for that). A reasonable requirement is still a hit — with no halt-and-ask primitive, an unsupplied precondition is met by a confident guess reported as a performed check, which is indistinguishable from the real thing.

## Self-review

If any reviewed surface was authored or edited in this session:

1. Fluency and memory of writing are zero evidence — re-read the file from disk; support every conclusion about it with a verbatim quote + path.
2. Never score such a surface GOOD/PASS without at least one cited mechanical check (a syndrome pass, claim diff, or command run).
3. State the self-review condition in the output, and take a fresh-context pass: something with **no session history**, handed three things and no more: the surface paths, the syndrome set to apply (§ Instruction-artifact syndromes, above), and — when its findings must be tagged — each tag vocabulary with the path it lives at — never the reasoning behind the surface, which re-contaminates the pass with the context it exists to escape. Its return is evidence to adjudicate, not a verdict to adopt. The capability is what this rule depends on, never a particular agent: which mechanism the host offers, how to detect it, and what to record when it offers none, live in `reference/bindings.md` (Fresh-context adjudication pass). A same-context reread is item 1's requirement, never a substitute for this one.

## Documentation stewardship

Choose the smallest correct surface, preferring higher ladder rungs:

```txt
machine-enforceable rule        -> test, type, schema, lint/check, CI, hook   (prefer)
directory/layer-scoped guidance -> nested CLAUDE.md (co-located, on demand)
file-type/cross-cutting rule    -> .claude/rules/*.md with `paths:` glob
always-relevant global rule     -> root CLAUDE.md (<200 lines)
repeatable procedure            -> a skill
domain/product intent           -> co-located *.spec.md
public API contract             -> JSDoc/TSDoc
cross-tool portability          -> AGENTS.md as source, imported/symlinked by CLAUDE.md
```

Add docs only when they cut future ambiguity more than they add context cost. A doc is **stale** when it: names commands that don't exist; contradicts package scripts or CI; describes removed APIs; repeats type shapes that changed; conflicts with a closer-scoped instruction; or asserts behavior not covered by tests or current code.

## JSDoc/TSDoc policy

Document invariants, side effects, fail-open/closed behavior, security/permission/billing/data semantics, deprecations, misuse-preventing examples, and behavior types can't express. Don't mandate exhaustive JSDoc on trivial exports (context cost + duplicates the signature); a repo rule that does is a flaggable quality claim. Don't assert guarantees stronger than the code enforces: if a comment says "never/always/must/throws/pure/idempotent/fail-closed/safe", verify code/tests enforce it — else soften the wording or raise a finding.
