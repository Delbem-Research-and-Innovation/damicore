# Maestro

Maestro is Devanity Open's default entrypoint for an end-to-end software change. It compiles a sufficient **Change Contract** before material coding and routes only the capabilities the change needs.

## Install

```bash
npx skills add TriangulosTecnologia/devanity-skills --skill maestro --agent claude-code
```

## Use

```text
/maestro <goal>
```

The current slice must be decision-complete, architecture-aware, proof-ready, bounded, and within its authority ceiling.

## Protocol

- [`reference/protocol.md`](reference/protocol.md) — Change semantics and lifecycle.
- [`reference/change.schema.json`](reference/change.schema.json) — interchange schema.
- [`reference/runtime.md`](reference/runtime.md) — routing, preflight, authority, proof, and execution.

No managed Devanity service is required.
