# Guardian — Platform bindings (Claude Code)

These are the platform-specific mechanics Guardian relies on. The methodology (basis-form, dimensions, severity, the ladder rungs) is agent-agnostic; **this file isolates the Claude Code platform mechanics and is the primary file to swap when porting.** The durability ladder and doc-stewardship name Claude surfaces (`CLAUDE.md`, `.claude/rules`) as examples of the path-scoped rung — swap those names too; the rest of the skill stands.

## Instruction surfaces & loading

- Root `CLAUDE.md` (or `.claude/CLAUDE.md`) loads in full at session start; nested `CLAUDE.md` in subdirectories load on demand when a file there is read (co-located, directory-scoped).
- `.claude/rules/*.md` with `paths:` glob frontmatter are file-type/path-scoped (load when a matching file is read); without `paths:` they load always-on, like `.claude/CLAUDE.md`.
- `@import` in `CLAUDE.md` expands at launch (no context saving).
- Claude Code does not read `AGENTS.md` natively; import it (`@AGENTS.md`) or symlink.
- Precedence between a nested `CLAUDE.md` and a path-scoped rule for the same file is undefined — avoid overlap.
- Other tools' surfaces to discover during the Deep baseline: `.github/copilot-instructions.md`, `.github/instructions/**`, `.cursorrules`, `.windsurfrules`, `.devin/rules/**`.

## Enforcement mechanisms

`CLAUDE.md`/rules/skills are context, not enforcement — to block regardless of the model, use a hook. Where a check runs and what can block:

```txt
before a dangerous action      → PreToolUse hook (exit 2 blocks the call)
before stopping without checks  → Stop hook
after an edit, to flag/suggest  → PostToolUse hook (cannot prevent; advisory)
```

## Execution trust

The Tool policy's origin rule (`SKILL.md`) is propose-and-stop: the skill requires the gate, it never provides protection. Three distinct things, never conflated:

- **Workspace separation** — a discardable `git worktree` protects the primary working tree and nothing else: code running in one still reads credentials, reaches the network, and touches services. A worktree is not a sandbox.
- **Execution isolation** — only a platform sandbox (restricted filesystem, network, secrets, processes) contains untrusted code; whether one exists is a platform fact to state, never to assume.
- **Human consent** — confirmation records that the human accepted the exposure; it mitigates nothing. The acceptance decision's options map here: *sandboxed* needs real isolation, *confirmed risk* is consent with the residual exposure named.

## Interactive menus

The `SKILL.md` **Interactive menus** rule (when a run may close with a chooser, and the anti-flooding limits) is realized here with the `AskUserQuestion` tool: a menu is the projection of an emitted `[DECIDE]` block (`reference/format.md` Decision format) — each option is a label mapping 1:1 to one of the block's `options:`, i.e. the `/guardian …` command the user would otherwise type (e.g. `improve <G-NNN|key>`, a mode, or a sub-scope), plus the block's no-op ("stop here"). This is the swap point when porting — replace it with the host agent's chooser, or drop it entirely: the text next-step line is always emitted and is the source of truth, so removing the menu changes nothing about correctness.

Detecting a **non-interactive** run (where the menu must be skipped): a headless invocation — `claude -p`, or any CI workflow — has no interactive channel; end with the text next-step only. A manual `/guardian` in a terminal or web session is interactive. When in doubt, skip the menu (the text next-step never regresses).

## Skill mechanics

- A skill's directory name is its command (`.claude/skills/guardian/` → `/guardian`). Its `SKILL.md` body stays in context for the whole session once invoked, so keep it lean and put depth in on-demand reference files; reference the skill's own files as `${CLAUDE_SKILL_DIR}/<path>`. This "stays in context" guarantee is what each mode file's Contract line checks against: on Claude Code the re-read is skipped; a host without the guarantee re-reads `SKILL.md` every run — the mode files are the reliable landing point, so the Contract line lives there, never only here.
- `$ARGUMENTS` in a skill body is substituted **literally** at invocation (empty string if none) — write parsing rules that survive empty / one / many tokens, never sentences that embed `$ARGUMENTS` as a noun.
- `disable-model-invocation: true` = manual `/name` only.
- `allowed-tools` grants (does not restrict) tools without a prompt while the skill is active; `disallowed-tools` removes tools from the pool.
