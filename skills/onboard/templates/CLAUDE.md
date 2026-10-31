# CLAUDE.md

<One paragraph: what this project is, who uses it, the main flow. Prototype or production.>

## Commands
<exact commands, one per line, from the repo's own config>
- Run: `…`
- Tests: `…`
- Lint: `…`
- Type check: `…`
- Migrations: `…`

## Architecture
<entry points, layers, data stores, external services; a request path in one line>

## Non-negotiable rules
<project-specific, short, enforceable where possible>
- …

## Where the detail lives
- `docs/…` — …
- `.claude/rules/` — topic rules, loaded by path

## Factory
This repo uses the "That's What We Shipped" workflow: `/factory` for features, `/quickfix` for small fixes.
Planning files: `docs/planning/specs/`, `docs/planning/plans/`. Guards read `docs/planning/active-scope.json` and `.claude/factory.json`.
