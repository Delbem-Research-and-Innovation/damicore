# Mode: docs

Contract: `SKILL.md` governs this run — if the host does not keep it loaded in context (`reference/bindings.md`), re-read it before anything else.

Review/improve the repo's context/instruction surfaces. A **surface = one file** (for a JSDoc/TSDoc target, one file's doc blocks). Submodes: `review` (diagnose — with a file path, that one surface; with a directory path, the full-review contract bounded to the surfaces beneath it, always Deep bounded to that directory (`reference/baseline.md`); with no path, the **full review**: every instruction surface, the instruction-surface projection of `audit`, always Deep baseline), `improve` (edit one approved surface — a JSDoc/TSDoc target is just a surface whose doc blocks are the content; Core rule 7 applies). The Action axis (`SKILL.md`) governs which submodes write, and its one-approved-unit rule has a corollary here: a fix that must write beyond the one approved surface (create or edit a second file) is never a `docs improve` — route it as `improve <finding>`, where the approved unit is the finding and may span files.

Steps: inspect the surfaces in scope; run the instruction-artifact syndromes on each (`reference/methodology.md`); identify the ambiguity/failure mode the doc should reduce; choose the smallest correct surface (stewardship table in `reference/methodology.md`); ensure surfaces are themselves written in basis-form and, where a basis-form rule belongs in a durable surface and is missing, write it there (propagate — `reference/basis-form.md`); prefer enforceable structure over prose; remove/propose removal of stale/duplicated text (stale criteria in methodology); verify any asserted behavior or recommend a test.

Required-fixes/Suggested-improvements entries use the finding format (`reference/format.md`) and **Output discipline** (SKILL) — instruction findings anchor as `path:heading:dimension:rule`. Emit a `[DECIDE]` block (SKILL Decisions) for each stop-and-ask owed — an unaccepted P0 and each P0/P1 whose fix is a trade.

Verdicts: a single-surface `review` and `improve` use the four ranked verdicts from `SKILL.md`. The full review emits `DOCS_BACKLOG` — the instruction-surface mirror of `audit`'s `AUDIT_BACKLOG`: the verdict names the run's shape (an inventory, not a gate on one unit), not its severity; every P0 still surfaces in full under Required fixes — **only when every discovered surface is dispositioned** `reviewed | absent`. When the sweep cap fires (`reference/baseline.md` sweep rules — in-scope surfaces exceed ~15), the run instead ends with the complete inventory (unread surfaces dispositioned `pending (batch k)`), a `[DECIDE][blocking][G-###][scope]` whose `options:` are the proposed batches — each one a bounded `docs review <directory>` — and the Verdict line `none — scope decision owed`; with no verdict emitted, `pending` is not a coverage claim (Core rule 10). A capped run captures the run manifest (`reference/baseline.md`) and each later batch re-verifies it before reading: a changed surface returns its batch to `pending`, and batches examined against different manifests never reconcile — the same rule `review` applies to groups. `DOCS_BACKLOG` is owed by the run that completes the last batch, reconciling the inventory across the session's batch runs (DIAGNOSE reads the transcript — Action axis); across sessions the scope decision is proposed for tracker promotion like any undecided `[DECIDE]` (`reference/format.md` — proposed, never written by DIAGNOSE), and the inventory's coverage restarts unless the user supplies a still-valid checkpoint (`reference/baseline.md`).

For the full review, prepend `### Surfaces found / reviewed`: one line per surface from the Deep baseline list — disposition `reviewed | absent` (or `pending (batch k)`, only in a capped run, which emits no verdict), and for reviewed surfaces the enforced/prose-only status. A discovered surface missing from this section means unchecked — a defect in the run, not an allowed omission. An all-`absent` inventory does not end the run: the full review still reconciles the repo's rules in force (`reference/baseline.md` Reconciliation), and each rule evidenced without an agent-legible surface or enforcement is a finding like any other — `docs improve <surface>` then creates the missing surface.

```md
### Verdict PASS | PASS_WITH_FIXES | PASS_WITH_ACCEPTED_RISK | BLOCK (single surface / `improve`) | DOCS_BACKLOG (full review) | none — scope decision owed (capped full review)

### Surfaces found / reviewed (full review only)

### Context cost LOW | MEDIUM | HIGH

### Ambiguity reduced

### Recommended surface enforcement | nested CLAUDE.md | .claude/rules | root CLAUDE.md | skill | \*.spec.md | JSDoc/TSDoc | AGENTS.md

### Required fixes [P0/P1][dominant|trade][G-###][dimension][rung] title + detail tier (finding format, `reference/format.md`; P0 first, then P1) ...

### Suggested improvements [P2/P3][dominant|trade][G-###][dimension][rung] title — one line each ...

### Decisions [DECIDE] blocks, only when a decision is owed (SKILL Decisions)

### Patch or proposal

### Verification needed and, when a check ran, its command · result · side effect (Action axis)
```

## Example

`docs review` of a bloated root `CLAUDE.md`.

```md
### Verdict PASS_WITH_FIXES

### Context cost HIGH

### Ambiguity reduced
CLAUDE.md is 420 lines; most is a per-directory list — a case-enumeration where a path-scoped rule belongs.

### Recommended surface .claude/rules
Move the `src/api/**` conventions to `.claude/rules/api.md` with a `paths:` glob (loads on demand).

### Required fixes
- **[P1][trade][G-001][instruction-hygiene][path-scoped-context] Per-directory case-list bloats the always-loaded surface**
  - fix: extract the API section to `.claude/rules/api.md` (`paths:` glob); delete the 3 stale commands; leave a one-line pointer  ·  CLAUDE.md:12
  - Key: CLAUDE.md:api-conventions:instruction-hygiene:global-case-list
  - why: lines list conventions per directory, and 3 named commands are absent from package.json (stale) — context cost every session, stale commands mislead agents.
  - basis: trade — improves context cost (the 420 always-loaded lines shrink); open premise: the `paths:` glob actually loads when an `src/api` file is edited — unverifiable before the file exists; verification cost: one edit under `src/api` after applying.

### Suggested improvements
- [P2][trade][G-002][instruction-hygiene][path-scoped-context] Test conventions could move to a nested CLAUDE.md under `src/` — Key: CLAUDE.md:test-conventions:instruction-hygiene:global-case-list

### Decisions
- **[DECIDE][blocking][G-003][trade] Move the API conventions out of the always-loaded surface?**
  - decision: whether cutting always-loaded context cost is worth an unverified loading premise — the fix stays a trade until the `paths:` glob is proven to load.
  - context: anchors G-001 — the fix writes two surfaces (edits `CLAUDE.md`, creates `.claude/rules/api.md`), so it routes as `improve G-001`, never as `docs improve CLAUDE.md` (one approved surface only).
  - options: apply → `/guardian improve G-001`, then close the premise by editing an `src/api` file · trim only → delete the 3 stale commands in place (single-surface `docs improve CLAUDE.md`), defer the move · defer all → dormant, worth doing when context cost is felt again.
  - recommendation: apply — trimming alone leaves the 420-line case-list untouched, the concrete pain.
  - if undecided: re-fires on the next docs review; the stale commands keep misleading agents meanwhile.

### Patch or proposal
(proposal — `docs review` is read-only; the cross-surface fix applies via `/guardian improve G-001`, a trade: it stops for the confirmation above)

### Verification needed
After applying: edit a file under `src/api` and confirm the moved rules load — closing the trade's open premise.
```

Full `docs review` of a repo with **zero instruction surfaces**, where READMEs and this session's decisions establish three conventions (no cross-imports between `pkg_*` packages; single workspace lockfile; per-package `make dev/check/test/clean`).

```md
### Verdict DOCS_BACKLOG

### Surfaces found / reviewed
Every Deep-baseline surface — absent.

### Context cost LOW

### Ambiguity reduced
No surface to drift — but three rules are in force with no agent-legible home (Reconciliation: in force + unstated + unenforced).

### Recommended surface enforcement
The import ban is mechanizable today; the other two seed a root `AGENTS.md` (<200 lines).

### Required fixes
- **[P1][trade][G-001][boundary-integrity][enforcement] Cross-import ban between `pkg_*` packages held only in README**
  - fix: add an import-restriction lint (crosswalk check) and wire it into CI  ·  README.md:24
  - Key: README.md:package-boundaries:boundary-integrity:unenforced-boundary
  - why: the rule is in force (README + this session's decision) but nothing can fail when an agent reintroduces a cross-import — pattern inertia propagates the violation silently, and no reviewer will see it in a point-in-time diff.
  - basis: trade — improves boundary enforcement, and the read-only import scan across `pkg_*` this session found zero existing cross-imports, so the lint lands green with no runtime surface; but the fix adds a lint config surface and a CI phase this repo does not have yet — beyond de minimis by structure, with no repo budget or measurement to price them, so the cost stays an open premise for the human (SKILL Fix classification).

### Suggested improvements
- [P2][trade][G-002][instruction-hygiene][prose] Decided conventions (lockfile, Makefile contract) have no agent-legible surface — seed a root `AGENTS.md` from the READMEs — Key: repo:agent-instructions:instruction-hygiene:unstated-rule-in-force

### Decisions
- **[DECIDE][blocking][G-003][trade] Take on this repo's first enforcement surface to gate the package boundary?**
  - decision: whether the cross-import ban becomes deterministic enforcement — a lint config plus a CI phase the repo does not have — or stays a rule held in words for now.
  - context: anchors G-001 — the ban is in force (README + this session's decision) and nothing can fail when it is violated; with no lint config or CI today, the fix is beyond de minimis and its cost is unpriced.
  - options: adopt → the boundary fails on violation; the repo gains a lint config and a CI phase to maintain · seed the surface only → record the ban in a root `AGENTS.md` (prose rung), no toolchain cost, no gate · defer → dormant, worth doing when the first cross-import lands.
  - recommendation: adopt — the scan proves the rule already holds, so the gate lands green and only stops regressions; whether the repo's first toolchain cost is worth paying is the human's call.
  - if undecided: G-001 stays open, re-fires on the next docs review, and the ban keeps depending on reviewer attention.

### Patch or proposal
(proposal — read-only; `/guardian improve <key>` for the lint — a trade, so it stops for the confirmation above — and `/guardian docs improve AGENTS.md` for the surface)

### Verification needed
The new lint must fail on a deliberate cross-import before it counts as enforcement (oracle fidelity).
```

The anti-example: concluding "no P0/P1 possible without a surface to violate" — surface absence bounds the syndromes, never reconciliation or severity.
