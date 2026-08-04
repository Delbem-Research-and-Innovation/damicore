# Guardian — Output format

The rendering contract for everything Guardian emits. Two first-class objects — the **finding** (a fact about the repo, adjudicated by the methodology) and the **decision** (a choice owed to a human across the authority boundary) — share one anatomy: a scannable headline over a nested detail tier. Compose order is unchanged (`SKILL.md` Compose order vs. render order): this file governs only how composed results render.

## Rendering principle

Structure is carried by **markdown list nesting**, never by bare indentation or blank-line adjacency: a full-form object is one list item whose headline is the bolded first line and whose detail tier is its nested sub-list. This is the one encoding whose two-tier hierarchy survives every medium Guardian output lands on — the terminal, rendered markdown (PR comments, issue bodies), and mechanical parsers (the format's own CI validation among them). Never render findings or decisions as loose paragraphs, and never rely on leading spaces to mean hierarchy.

## Finding format

```txt
- **[P0–P3][dominant|trade][G-###][dimension][rung] Title**   ← headline: all five axes, one line
  - fix: <the one action> · <path:line>                        ← ephemeral navigation, this session
  - Key: <path>:<symbol-or-heading>:<dimension>:<rule>         ← durable identity, never a line number
  - why: <evidence + risk, framed by the crosswalk axis>
  - basis: <fix-class justification>
```

Headline axes, in order — each judges a different thing; the axes never mix:

- **Severity** `P0–P3` — judges the finding (`SKILL.md` severity table).
- **Fix-class** `dominant|trade` — judges the fix; always present, adjacent to severity but a distinct axis (`SKILL.md` Fix classification).
- **`G-NNN`** — a session-local **alias** for the durable key, which is the canonical identity. Numbering continues across runs within a session — never restart at `G-001`. A stale or cross-session `G-NNN` does not resolve: use the key or an unambiguous suffix of it.
- **Dimension** — exactly one of the 8 slugs in `reference/methodology.md`; the only lens tag (a basis-form test name is never a finding tag).
- **Rung** — the target ladder rung: `enforcement|path-scoped-context|procedure|prose` (`prose` is the human-review rung — a rule stated only in words).

Detail tier fields:

- `fix:` the one action + a clickable `path:line` — ephemeral, for navigating now.
- `Key:` the durable key `path:symbol-or-heading:dimension:rule` — a structural anchor (never a line number) so it survives edits and new sessions.
- `why:` evidence + risk, framed by the crosswalk axis the finding maps to, never by the call site's surface label (`reference/methodology.md` Axis-cited classification — cite the test, run the swap-test before the tags are final).
- `basis:` the fix-class justification — the envelope checked plus any costs accepted as de minimis (dominant), or the terms (trade).

**One-line form** (P2/P3, and each P1 past the full-form cap): the full five-axis headline — the key never substitutes for any axis slot — then the title, then the key, and no detail tier:

```txt
- [P2][trade][G-007][pattern-hygiene][prose] Title — Key: <path>:<symbol>:<dimension>:<rule>
```

Exception: a one-line **dominant** also carries its check inline (`— basis: <what was checked>`); without that clause the class is trade.

The two forms are **exclusive**, and CI enforces the boundary structurally: a full-form headline opens **and closes** its bold and carries each mandatory field as its own nested list item, exactly once — extra nested items are fine (`review` lists instances under Evidence); a one-line object keeps every field on its headline and grows no nested item at all. Likewise for decisions — `blocking` always renders full-form, `dormant` always one line. The detail tier is the indented block immediately below the headline, so no object can borrow a field from what follows it.

For durable/team tracking, promote a finding into the existing issue tracker/TODOs — never a bespoke backlog file. **Promotion is proposed, not performed**: DIAGNOSE writes no external record (Action axis), so Guardian drafts the entry and the human (or an ACT run the user explicitly asked for) creates it. A promoted entry carries the open question and the durable key — never a coverage claim: a later session re-establishes coverage itself (Core rule 10).

## Decision format

A `[DECIDE]` block is emitted at every point where Guardian owes a human a choice, giving one form to the stop-and-asks the skill defines. Those triggers are enumerated once, in `SKILL.md` **Decisions** — this file governs only how the block renders, so a new stop is added there and inherits this form automatically. It never creates a new stop; it renders an existing one.

The block transfers the **decision space, not the case**: it must be decidable from the block alone by someone without this run's context. The human decider is the one consumer with less context than the producer — write the block at emission time, while that context is in hand and free.

```txt
- **[DECIDE][blocking|dormant][G-###][rule|trade|acceptance|scope] Question, one line**
  - decision: <the choice at stake, at the rule/axis level, in product terms — never the instance>
  - context: <why it surfaced, one line of evidence — the instance belongs here> · anchors <G-NNN or Key, when it rides on a finding>
  - options: <A → durable consequence> · <B → durable consequence> (2–4; include a no-op; consequences name what becomes durable where — codify at <surface>, severity change, applied fix)
  - recommendation: <Guardian's pick + its basis — labeled, never pre-selected>
  - if undecided: <the visible fate — never silent disappearance>
```

- **Status** — `blocking`: owed this run; its `if undecided:` names the fate (verdict stays BLOCK, re-fires on the next run, or is proposed for tracker promotion as an open decision — the same promotion rule findings use). `dormant`: explicitly allowed to sleep — a deferred trade or a P2/P3 opportunity; its `if undecided:` is its activation condition (`worth doing when <pain observed>`). Deciding "defer" converts a blocking decision into a dormant one-liner.
- **Kind** — `rule` (a recurring rule or product intent — a yes resolves to `<rule> → codify at <surface>`), `trade` (a fix-class trade confirmation), `acceptance` (a human taking on a risk Guardian will not assume on its own authority — an unfixed P0/P1, or exposure from an action such as running untrusted code; record who/what/why and any compensating control. Accepting a finding additionally sets `PASS_WITH_ACCEPTED_RISK` and owes a follow-up/expiry; accepting an action records the residual exposure, since confirmation is acceptance, not containment — `reference/bindings.md`), `scope` (what falls inside or outside this run's unit — routing, submode, an audit sub-scope, or absorbing an unexpected change into an approved unit).
- **G-numbering is shared with findings** — one session sequence, so `improve G-NNN` and a decision answer never collide.
- **Anchor, don't repeat**: a decision riding on a finding cites it (`anchors G-NNN`) and adds only what the finding lacks — the rule-level question, the options with consequences, the recommendation, the fate. Evidence stays in the finding's `why:`.
- **One-line dormant form**: `- [DECIDE][dormant][G-###][trade] Title — worth doing when <pain observed> — anchors <Key>`.
- The interactive closing menu is this block's **projection**: menu options map 1:1 to `options:` (`reference/bindings.md` Interactive menus). The emitted text block is the source of truth; the menu is disposable.
- Authority boundary (`SKILL.md`): the block presents the axes of the choice; it never pre-decides product intent. The recommendation exists, labeled — it is not a default.

## Section conventions

- The verdict value sits on its heading line (`### Verdict BLOCK`); every other section puts its value on the lines below the heading.
- An **empty section renders the single line `none`** (optionally `none — <one-clause reason>`) — never omit the heading: an absent section reads as unchecked, not empty.
- `### Decisions` renders after all findings and before the closing next step, **only when at least one decision is owed** — the one section whose absence means "none owed". Blocking decisions render full, in the severity order of their anchors; dormant ones one line each.
- Findings render per `SKILL.md` **Output discipline**: strict severity order, prose never between findings, P0 full, P1 top-3 full + rest one-line, P2/P3 one line each.
