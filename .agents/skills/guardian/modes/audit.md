# Mode: audit

Contract: `SKILL.md` governs this run — if the host does not keep it loaded in context (`reference/bindings.md`), re-read it before anything else.

Bounded health review; require a scope (ask if missing). The target is the **working tree** in scope — tracked files plus untracked (`??`) ones, gitignored excluded — the same definition the baseline uses for a change. Probe first, NUL-safe so paths with spaces survive: `git ls-files -z <scope> | tr '\0' '\n' | grep -c .` for the tracked count (add untracked from `git status --short <scope>`), and `git ls-files -z <scope> | xargs -0 wc -l | tail -1` for volume. Binary or generated files are enumerated but neither line-counted nor syndrome-swept, and are named with that reason. The bound is the **exhaustive contract** — every file read, every syndrome applied, all 8 dimensions scored with a cited check — not a fixed count; beyond ~100 files or ~30k total lines the contract degrades silently (heuristics; the human may override): propose 2–4 sub-scopes by seam (package/layer/domain) — interactive: offer them as a menu (`reference/bindings.md`) — and audit one. Narrowing trades holism for depth: the syndromes that live **between** sub-scopes — duplication across them (irreducible), dependency cycles between them (orthogonal) — are invisible to every sub-audit. So when narrowing, still run any repo-wide mechanical check the repo already has (duplication detector, import/dependency-graph lint) at full width, and record cross-scope checks not run under Coverage. Steps:

1. Run the Deep baseline (`reference/baseline.md`); disposition every item (`enforced`/`prose-only`/`absent`).
2. Enumerate every file in scope; apply the applicable syndrome set to each — code: the crosswalk checks (`reference/basis-form.md`); instruction surfaces incl. skill files: the instruction-artifact syndromes (`reference/methodology.md`). When the scope is itself an instruction artifact, its files are the surface set for reconciliation.
3. Status **all 8 dimensions**, one row each — the status is derived from this run's open findings, never judged separately: examined (a cited performed check — command run, per-file sweep, claim diff — and its result) → `GOOD` (no open finding) | `WEAK` (only open P2/P3) | `BAD` (≥1 open P0/P1; human-accepted → render `BAD — accepted risk`, never upgraded: acceptance changes governance, not the repo). `UNKNOWN` is a disposition, not an escape hatch: it means the dimension was addressed and the evidence is insufficient or unavailable — no discriminating check exists, or running it is unsafe/needs approval — with that reason cited. A relevant dimension skipped for time or capacity is **not dispositioned**: the run ends `### Verdict none — audit completion pending` and proposes a narrower scope or batches (SKILL Completion invariant) instead of emitting `AUDIT_BACKLOG`. No cited check → `UNKNOWN`, never `GOOD`. The Evidence column cites the check; a status contradicting its dimension's findings is a defect of the run. Omitted rows are not allowed.
4. Reconcile declared-vs-enforced; check boundary enforcement.
5. List findings in the finding format (`reference/format.md`, incl. `Key:`); emit a `[DECIDE]` block (SKILL Decisions) for each stop-and-ask owed — an unaccepted P0 and each P0/P1 whose fix is a trade; propose a safe sequence.

Output — render findings per SKILL **Output discipline** (every P0 full; P1 top 3 full, each extra as a one-line finding; P2/P3 one line each, or counts per dimension when >~5); never hide blockers; name the first safe improvement as a runnable command.

```md
### Verdict AUDIT_BACKLOG | none — audit completion pending (a relevant dimension skipped for capacity — step 3)

### Scope audited

### Coverage files read · checks applied, with results and — for any that executed project code — its side effect · explicitly not checked

### Baseline every item dispositioned enforced / prose-only / absent, where enforcement runs

### Dimension status | Dimension | Status (GOOD/WEAK/BAD[ — accepted risk]/UNKNOWN, derived from open findings — step 3) | Evidence (cited check + result, or UNKNOWN reason) | — a markdown table (header + separator row), all 8 rows

### Required fixes all P0s · top-3 P1s in full (finding format, `reference/format.md`) · every further P1 as a one-line finding

### Suggested improvements [P2/P3][dominant|trade][G-###][dimension][rung] title — one line each, or counts per dimension when >~5

### Decisions [DECIDE] blocks, only when a decision is owed (SKILL Decisions)

### Suggested sequence

### First safe improvement (a runnable `/guardian improve <ref>` command)

### Do-not-touch without approval
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
- [P1][trade][G-002][executable-spec][enforcement] "money integers" rule unenforced — Key: CLAUDE.md:money-rule:executable-spec:prose-only

### Suggested improvements
none in examined dimensions

### Decisions
- **[DECIDE][blocking][G-003][trade] Is "money integers" a contract worth an enforcement gate?**
  - decision: whether the CLAUDE.md rule is durable intent (→ enforce) or a stale preference (→ demote) — product intent, not methodology.
  - context: anchors G-002 — the rule is in force in CLAUDE.md, but nothing can fail when it is violated.
  - options: enforce → `/guardian improve G-002` (lint/test gate; adds a CI check) · demote → rewrite the CLAUDE.md line as guidance, close G-002 · defer → dormant, worth doing when the next money bug lands.
  - recommendation: enforce, after G-001 — G-001's failing case already proves the pain the rule guards.
  - if undecided: proposed for tracker promotion as an open decision (the human records it); re-surfaces on the next audit.

### Suggested sequence
G-001 first (high-risk), then G-002 per the decision above.

### First safe improvement
Run `/guardian improve G-001` — smallest change with the highest risk reduction.

### Do-not-touch without approval
The Stripe webhook signature check (high-risk class).
```
