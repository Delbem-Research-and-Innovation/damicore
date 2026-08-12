# ARCHER

ARCHER is Devanity Open's architecture capability. It designs or revises architecture from required properties and semantics, then derives state, boundaries, failure behavior, enforcement, evidence, and revision conditions.

## Install

```bash
npx skills add TriangulosTecnologia/devanity-skills --skill archer --agent claude-code
```

## Use

```text
/archer <system, change, or architecture question>
```

Examples:

```text
/archer design the architecture for a generic closed-loop control platform
/archer add multiple payment providers without duplicating payment semantics
/archer review whether this proposed service boundary is justified
```

ARCHER first classifies significance:

- A0 — local implementation; no architecture cycle required;
- A1 — conforming extension of an explicit existing decision;
- A2 — material architecture decision; run the six-phase method.

It is directly usable and also serves as the architecture owner when Maestro routes an A2 change.

[`reference/method.md`](reference/method.md) is the self-contained operational method shipped with the skill.
