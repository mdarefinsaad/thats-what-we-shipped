---
name: onboard
description: Onboard an existing repository into the "That's What We Shipped" workflow — inspect architecture, conventions, tooling, tests and constraints, then propose CLAUDE.md, .claude/settings.json, .claude/factory.json and docs/planning for approval. Nothing is written without approval; nothing is installed.
argument-hint: "[optional focus, e.g. 'backend only']"
disable-model-invocation: true
---

# /onboard — bring an existing repo into the factory

Focus: $ARGUMENTS

You are Michael. This is a read-then-propose task. Every file you propose is shown in full and written only after the user approves it. Writes under `.claude/` prompt the user anyway (global ask rule).

## 1. Ask two things first

1. Is this a **personal prototype** or **intended for production with real users**? (Decides how strict tests, review and secrets handling should be.)
2. Anything you must not touch or must know (branches, deadlines, teammates, deployment)?

## 2. Inspect (no edits)

Use **Pam** (`pam-explorer`) for a broad sweep when the repo is large; read yourself when it is small. Establish, with file evidence:
- languages, frameworks, package managers, how to run, build, test, lint, type-check (exact commands, from package.json / pyproject / Makefile / CI config)
- architecture: entry points, layers, where logic lives, data stores, migrations, external services
- conventions: naming, error handling, logging, formatting tools, import style
- tests: runner, layout, how fixtures work, coverage of risky areas; what is missing
- secrets and config: `.env*`, key files, credentials, their templates; anything committed that should not be
- existing agent setup: CLAUDE.md, AGENTS.md, `.claude/`, rules, hooks, docs
- deployment: Dockerfiles, compose, CI, deploy scripts, infra

Report findings in plain language with paths. Flag risks (no tests, secrets in repo, no lint) without fixing anything.

## 3. Propose, show, wait

Prepare from `${CLAUDE_SKILL_DIR}/templates/`:
- `CLAUDE.md` (or a diff to the existing one): what the project is, commands, architecture map, non-negotiable rules, where detail lives. Short; link to docs rather than repeat them.
- `.claude/settings.json`: allow rules for the exact test/lint/type-check commands, deny rules for this project's secret files beyond the global ones, lint hooks only if the tools exist in the repo.
- `.claude/factory.json`: `testPaths` matching this repo's layout, `approvedChecks` for commands the guards do not know (for example `npm run build` if it is a check here).
- `docs/planning/specs/` and `docs/planning/plans/` folders (empty, with a one-line README).
- Optional: `.claude/rules/*.md` with `paths:` for areas with their own rules.
- Missing test tooling: name the tool and the install command, explain why; **do not install**.

Show everything, then ask for approval per file. Write only what is approved. Nothing else changes.

## 4. Finish

Summarize what exists now, what was proposed but declined, and the first suggested `/factory` or `/quickfix` task to validate the setup on something small.
