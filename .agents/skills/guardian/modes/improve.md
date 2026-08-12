# Mode: improve

Contract: `SKILL.md` governs this run — if the host no longer keeps it loaded in context, re-read it before anything else.

Fix exactly one approved finding, by ladder position (`reference/enforcement.md`). Resolve the reference first:

1. Resolve the reference to a durable key (the canonical identity): a `G-NNN` present in this session's finding list → its key; a **full key** → resolves structurally, no session list required: it carries its own path, and steps 2–3 re-verify it from disk — that is what makes it the identity that survives sessions. An **unambiguous suffix of one** (e.g. `applyDiscount:verification-loop:missing-test`) → resolves against this session's finding list, the same one `G-NNN` resolves against. A suffix matching more than one is ambiguous: list the matches (interactive: offer them as a menu, `reference/bindings.md`) and ask. A suffix matching **none** does not resolve — that is every suffix in a fresh session, where no list exists yet, and a suffix has already dropped the path step 2 needs — so ask for the full key. Likewise a stale or cross-session `G-NNN` → ask for the key or re-run the diagnostic. Then read the **resolved** key right-to-left: last segment is the rule, second-last is the dimension; the remainder splits at its **first** colon into the path and the symbol/heading — right-to-left exactly so a colon inside a heading can never shift the dimension or rule. This parse never runs on a suffix as typed — a suffix is shorter by design, and turning it into a key is what the clause above does. A resolved key is malformed, so stop and ask rather than guess which was meant, when it carries fewer than four segments or when its dimension is not among the slugs the crosswalk names (`reference/basis-form.md`).
2. Read the path and locate the symbol/heading. If either no longer exists, stop and ask (or propose a narrow re-audit). This precedes step 3 deliberately: a deleted file makes the violation absent too, and the two outcomes must not collapse — reporting a vanished file as a resolved finding closes it on evidence that only shows the file is gone.
3. Re-verify the violation still exists in what you just read; if absent, report the single line `ALREADY_RESOLVED [<ref>] — <evidence run this session>` and stop (no write). If it exists but the evidence points to an undeclared invariant — the diverging behavior is intentional and the rule is stale (`reference/baseline.md` Reconciliation) — stop and report `RECLASSIFIED [<ref>] — <the stale rule + evidence>` plus the replacement finding, instead of writing.

Then fix:

- **Mechanizable** → codify the enforcement (lint/type/schema/test/coverage gate), not just patch the instance; first check the rule/plugin is already available; if a new dep or hook/CI change is needed, stop and propose.
- **Not mechanizable** → smallest correct prose/spec change, or produce a `plan` if it needs architectural/product judgment.
- **basis-form migration** → migrate case→basis or collapse an empty axis under the visible-axis guardrail (`reference/basis-form.md`); then promote the syndrome to a check (`reference/enforcement.md`).

The first two partition the space; the third cuts across both, so it takes precedence when it applies: a finding that is a basis-form migration **and** mechanizable migrates first and codifies after, because a check written against the case-list outlives the cases it was meant to remove.

**Oracle before fix.** When the unit adds or alters an **oracle** — anything whose job is to fail when the contract breaks: a test, type, schema, validator or lint rule, coverage threshold, CI gate — write the oracle **first** and run the focused check to watch it **fail against the unfixed code**, before writing the correction. An oracle nobody has seen fail is not an oracle, and one written after the code it judges cannot be told apart from one shaped to pass it. This is the mode that writes, so it is where that confusion is most expensive; the order removes it at no extra cycle, since the check has to run anyway. Three outcomes — only the second ends the unit here, and only the first continues without a human:

- **red** → the oracle discriminates. Write the correction, re-run, expect green.
- **green where red was expected** → the oracle does not test the thing. Stop before writing the correction; the oracle is the unit now.
- **no red state reachable** — the oracle would pass today because nothing violates it yet (a new lint rule over already-clean code). Produce one if it stays inside the unit: a deliberate violation, reverted before completion with the revert confirmed by the final capture (`reference/baseline.md`). Otherwise record `NOT FALSIFIED` + reason — the oracle's fidelity is then an unverified premise the fix depends on, so the class is **trade** (`SKILL.md` Fix classification) and it stops for a human like any other.

An erroring or crashing run is none of the three: it decides nothing about the oracle — repair the run first, and read an outcome only from a check that executed.

For a `verification-loop:missing-test` finding the red run is also the strongest available form of step 3: the violation is re-verified by the oracle failing on it, not by inspection.

**Classification order when the unit carries an oracle.** The class gates the ACT stop and the oracle's outcome can change it, so: classify **provisionally before any write**; a provisional *trade* stops there, before the oracle exists. A provisional *dominant* writes the oracle and runs it — the oracle is the instrument the decision needs, not the patch the stop is about — and a `NOT FALSIFIED` outcome makes the class *trade*, which stops before the correction. The stop always precedes the correction, and only the **trade-classification** stop may come after the oracle — every other stop (high-risk class, new dependency, hook/CI change; Core rule 7, Action axis) precedes **every** write, the oracle included.

Rules: one finding only; small patch; add/update verification if behavior changes; never mix feature work with repo-health cleanup; high-risk guard: Core rule 7; classify the fix before writing, per the order above (`SKILL.md` Fix classification) — a trade stops per the Action axis and renders its confirmation as a `[DECIDE][blocking][G-###][trade]` block (SKILL Decisions), the proposed patch beneath it. A structural change (many files or redrawn boundaries) is not one `improve`: run `plan`, then execute it as an ordered sequence of contained, verified `improve` steps.

**Verification side effects** — the verification command executes project code, and in ACT an unexpected write is not noise: it silently expands the approved unit. Follow the ACT projection of the target fingerprint (`reference/baseline.md`): name the expected file set before verifying, capture around it, and declare `Finding fixed` only once every delta is dispositioned and any changed expected file has been re-read.

```md
### Finding fixed [G-### or key]

### Ladder rung targeted enforcement | path-scoped-context | procedure | prose

### Files changed oracle: <the files whose job is to fail> · implementation: <the rest> — listed apart so the oracle diff can be read on its own

### Why this improves the AI Repo

### Fix class dominant (checked: <what>) | trade — the [DECIDE] block above carried its terms; record the human's answer

### Verification command / result both runs, this session — the oracle's red before the fix existed, then green after. One token per state, all four live: `n/a` when the unit carries no oracle · `focused check: none` when the repo declares none for these files (`reference/baseline.md`) · `NOT FALSIFIED` + reason when a check exists but no red state was reachable · `NOT RUN` + reason when one was reachable and still not run. Then the observed delta vs the expected file set — inventory **and** identity, since neither substitutes for the other (`reference/baseline.md`) — with any verification side effect dispositioned

### Residual risk

### Suggested PR description
```

## Example

Fixing `G-001` from the audit example. It alters what a billing path returns, so it is in the high-risk class: the invocation proposes and stops (Core rule 7), and only the confirmation authorizes the write.

```md
- **[DECIDE][blocking][G-005][acceptance] Authorize the cents fix to `sumLineItems`?**
  - decision: whether Guardian may write to the billing path — the authorization G-003 asked for at audit time, re-rendered here with the patch attached.
  - context: anchors G-001 — the patch changes the sum from float to integer cents and adds the failing case as a test — the two files under Files changed, below.
  - options: authorize → the oracle-first sequence runs and the fix applies · decline → the patch stays a proposal, G-001 stays open · test only → land the oracle, leave the arithmetic, re-decide with the failure recorded in CI.
  - recommendation: authorize — the failing case is already known, and the oracle lands with the fix rather than after it.
  - if undecided: nothing is written; G-001 re-fires on the next audit.
```

Authorized, the run proceeds and reports:

```md
### Finding fixed [G-001] (key: src/payments/totals.ts:sumLineItems:verification-loop:float-money)

### Ladder rung targeted enforcement

### Files changed
oracle: `src/payments/totals.test.ts` (new) · implementation: `src/payments/totals.ts` (sum in integer cents).

### Why this improves the AI Repo
Turns a prose rule ("money integers") into a test + type; the syndrome (non-spanning money math) now fails a check, not a human.

### Fix class
dominant (checked: the oracle was observed failing on the exact defect while the correction did not yet exist, so it discriminates rather than describes; no API, dependency, or behavior change beyond the fixed bug; one test file in the payments suite that already runs — no new phase, config, or boundary; de minimis, named).

### Verification command / result
`pnpm test --filter payments`, twice. Red, oracle only: 1 failed — `sumLineItems([10.10, 20.20, 30.30])` returned `60.599999999999994`, expected `60.60`. Green, after the fix: 6 passed. Captured around both runs: status delta matched the expected set (`totals.test.ts`, then `totals.ts`), and the diff hash changed only across the edits, not across either run — no verification side effect.

### Residual risk
Other modules may still do float money math — proposed a repo-wide follow-up finding, not fixed here (one finding per improve).

### Suggested PR description
"Fix float money arithmetic in sumLineItems; add cents-based tests."
```
