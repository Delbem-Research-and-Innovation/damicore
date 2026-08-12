# Mode: audit

Contract: `SKILL.md` governs this run — if the host no longer keeps it loaded in context, re-read it before anything else.

Bounded health review; require a scope (ask if missing). The target is the **working tree** in scope — tracked files plus untracked (`??`) ones, gitignored excluded. That is a wider set than the baseline's *change* (a diff, `reference/baseline.md`); the two share only how they treat untracked and gitignored files. Probe first, NUL-safe so paths with spaces survive, and over the whole target rather than its tracked half — `git ls-files` alone omits every untracked file the line above just included:

```txt
{ git ls-files -z "<scope>"; git ls-files -z --others --exclude-standard "<scope>"; } | tr '\0' '\n' | grep -c .   # file count
{ git ls-files -z "<scope>"; git ls-files -z --others --exclude-standard "<scope>"; } | xargs -0 cat | wc -l       # volume — one total, not one per xargs batch
```

The listing runs twice so the probe stays a pure pipeline — a scratch file would be a write the Action axis forbids (`SKILL.md`). The volume figure is a raw sizing heuristic: binary and generated files inflate it here and are excluded only at step 2, where they are enumerated but not line-counted. Binary or generated files are enumerated but neither line-counted nor syndrome-swept, and are named with that reason. The bound is the **exhaustive contract** — every file read, every syndrome applied, every dimension in `reference/methodology.md` scored with a cited check — not a fixed count; beyond ~100 files or ~30k total lines the contract degrades silently (heuristics; the human may override): propose 2–4 sub-scopes by seam (package/layer/domain) — interactive: offer them as a menu (`reference/bindings.md`) — and audit one. Narrowing trades holism for depth: the syndromes that live **between** sub-scopes — duplication across them (irreducible), dependency cycles between them (orthogonal) — are invisible to every sub-audit. So when narrowing, still run any repo-wide mechanical check the repo already has (duplication detector, import/dependency-graph lint) at full width, and record cross-scope checks not run under Coverage. Steps:

1. Run the Deep baseline (`reference/baseline.md`); disposition every item (`enforced`/`prose-only`/`absent`).
2. Enumerate every file in scope; apply the applicable syndrome set to each — code: the crosswalk checks (`reference/basis-form.md`); instruction surfaces incl. skill files: the instruction-artifact syndromes (`reference/methodology.md`). When the scope is itself an instruction artifact, its files are the surface set for reconciliation.
3. Status **every dimension listed in `reference/methodology.md`**, one row each, none omitted — the status is derived from this run's open findings, never judged separately: examined (a cited performed check — command run, per-file sweep, claim diff — and its result) → `GOOD` (no open finding) | `WEAK` (only open P2/P3) | `BAD` (≥1 open P0/P1; human-accepted → render `BAD — accepted risk`, never upgraded: acceptance changes governance, not the repo). `NOT RELEVANT` when the scope contains no artifact the dimension governs (`reference/methodology.md` relevance rule) — the reason cited like any other, and never a substitute for the two below. `UNKNOWN` is a disposition, not an escape hatch: it means the dimension **is** relevant, was addressed, and the evidence is insufficient or unavailable — no discriminating check exists, or running it is unsafe/needs approval — with that reason cited. A relevant dimension skipped for time or capacity is **not dispositioned**: the run ends `### Verdict none — audit completion pending` and proposes a narrower scope or batches (SKILL Completion invariant) instead of emitting `AUDIT_BACKLOG`. No cited check → `UNKNOWN`, never `GOOD`. When both apply — an open P0/P1 exists **and** further evidence is unavailable — `BAD` wins: the status is derived from open findings, and `UNKNOWN` speaks only where no finding already has. The Evidence column cites the check; a status contradicting its dimension's findings is a defect of the run. Omitted rows are not allowed.
4. Reconcile declared-vs-enforced; check boundary enforcement.
5. List findings in the finding format (`reference/format.md`, incl. `Key:`); emit a `[DECIDE]` block (SKILL Decisions) for each stop-and-ask owed — an unaccepted P0 and each P0/P1 whose fix is a trade; propose a safe sequence.

Output — render findings per SKILL **Output discipline** (every P0 full; P1 top 3 full, each extra as a one-line finding; P2/P3 one line each, or counts per dimension when >~5); never hide blockers; name the first safe improvement as a runnable command.

```md
### Verdict AUDIT_BACKLOG | none — audit completion pending (a relevant dimension skipped for capacity — step 3)

### Scope audited

### Coverage files read · checks applied, with results and — for any that executed project code — its side effect · `focused check: none` when the repo declares none (`reference/baseline.md`) · explicitly not checked

### Baseline every item dispositioned enforced / prose-only / absent, where enforcement runs

### Dimension status | Dimension | Status (GOOD/WEAK/BAD[ — accepted risk]/UNKNOWN/NOT RELEVANT, derived from open findings — step 3) | Evidence (cited check + result, or the UNKNOWN / NOT RELEVANT reason) | — a markdown table (header + separator row), one row per dimension in `reference/methodology.md`, none omitted

### Required fixes all P0s · top-3 P1s in full (finding format, `reference/format.md`) · every further P1 as a one-line finding

### Suggested improvements [P2/P3][dominant|trade][G-###][dimension][rung] title — Key: … — one line each in the one-line form (`reference/format.md`: the key always rides the headline; a one-line dominant adds — basis:), or counts per dimension when >~5

### Decisions [DECIDE] blocks, only when a decision is owed (SKILL Decisions)

### Suggested sequence

### Do-not-touch without approval

### First safe improvement (a runnable `/guardian improve <ref>` command — the run's closing next step, so it ends the report)
```

## Example

Scope `src/payments` (a slice — a full `src/` would be narrowed first via the probe).

```md
### Verdict AUDIT_BACKLOG

### Scope audited
src/payments (probe: 14 files, 2.1k lines)

### Coverage
Read 14/14 files; checks: per-file syndrome sweep, tsc config resolved, CI workflow read, claim diff CLAUDE.md vs scripts. Not checked: runtime behavior of the totals path (the CI test job runs, but no test covers it — that gap is G-001).

### Baseline
Enforced: strict TS (tsconfig), lint + unit tests (CI test job). Prose-only: "always use money integers" (CLAUDE.md) — no check. Absent: pre-commit hooks, coverage gate. Instruction surfaces: root CLAUDE.md only — no others found.

### Dimension status
| Dimension | Status | Evidence |
| --- | --- | --- |
| compressibility | GOOD | per-file sweep: max file 210 lines, no cross-layer logic |
| executable-spec | BAD | "money integers" rule prose-only (claim diff vs enforcement) — open P1 G-002 |
| co-located-spec | GOOD | totals.spec.md present, states non-goals |
| verification-loop | BAD | focused check: none for totals path — open P0 G-001 |
| boundary-integrity | GOOD | import sweep: payments never imported outside its package |
| pattern-hygiene | GOOD | per-file syndrome sweep (14/14): no copied workaround, no god file, no deepened nesting |
| debt-containment | GOOD | 1 TODO, visible and issue-linked |
| instruction-hygiene | GOOD | syndrome pass on CLAUDE.md: no hits |

### Required fixes
- **[P0][dominant][G-001][verification-loop][enforcement] Float arithmetic on money in `sumLineItems`**
  - fix: integer cents + test in the suite the CI test job already gates  ·  src/payments/totals.ts:31
  - Key: src/payments/totals.ts:sumLineItems:verification-loop:float-money
  - why: `10.10+20.20+30.30 !== 60.6`, no test — billing drift.
  - basis: checked — the failing case becomes the test; no API change; one deterministic case in a suite the CI test job already runs, so nothing in CI changes — no new dependency, phase, config, or boundary (de minimis, named).
- **[P1][trade][G-002][executable-spec][enforcement] "money integers" rule unenforced**
  - fix: add a lint rule banning float literals in `src/payments/**`, wired into the CI test job  ·  CLAUDE.md:31
  - Key: CLAUDE.md:money-rule:executable-spec:prose-only
  - why: CLAUDE.md states the rule and nothing can fail when it is violated — G-001 is that violation, shipped.
  - basis: trade — improves executable-spec, but adds a lint config surface this repo does not have; cost unpriced, and whether the rule is durable intent is G-004's open question.

### Suggested improvements
none in examined dimensions

### Decisions
- **[DECIDE][blocking][G-003][acceptance] Authorize a write to the money path to fix G-001?**
  - decision: whether Guardian may alter what the billing sum returns — an authorization it does not hold on its own (Core rule 7), not a technical choice.
  - context: anchors G-001 — `sumLineItems` is a billing path, so any change to its arithmetic is in the high-risk class; the fix is proposed, never applied by the `improve` invocation alone.
  - options: authorize → `/guardian improve G-001` proposes the patch and stops for this confirmation, then writes · decline → G-001 stays open and the float math keeps shipping · test only → add the failing case as a test, leave the arithmetic, and re-decide with the failure recorded.
  - recommendation: authorize — the defect is arithmetic with a known failing case, and the fix is smaller than the exposure it removes.
  - if undecided: verdict keeps its unaccepted P0; re-fires on the next audit.
- **[DECIDE][blocking][G-004][rule] Is "money integers" a contract worth an enforcement gate?**
  - decision: whether the CLAUDE.md rule is durable intent (→ enforce) or a stale preference (→ demote) — product intent, not methodology.
  - context: anchors G-002 — the rule is in force in CLAUDE.md, but nothing can fail when it is violated.
  - options: enforce → `/guardian improve G-002` (lint/test gate; adds a CI check) · demote → rewrite the CLAUDE.md line as guidance, close G-002 · defer → dormant, worth doing when the next money bug lands.
  - recommendation: enforce, after G-001 — G-001's failing case already proves the pain the rule guards.
  - if undecided: proposed for tracker promotion as an open decision (the human records it); re-surfaces on the next audit.

### Suggested sequence
G-001 first, once G-003 authorizes it; then G-002 per G-004.

### Do-not-touch without approval
Anything altering the billing path, `sumLineItems` included (that is G-003). The Stripe webhook signature check, which no finding here proposes touching.

### First safe improvement
Run `/guardian improve G-001` — smallest change with the highest risk reduction. It is high-risk class, so the invocation proposes the patch and stops at G-003 rather than writing.
```
