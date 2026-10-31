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
- The optional, generic project kit from the factory repo: offer it. Copied with `python3 <factory-repo>/install.py --project <this repo>`; existing files are kept.
  - `project/hooks/`: `lint_changed_file.py` and `forbidden_patterns.py` are driven entirely by `factory.json` (`lintOnEdit`, `forbiddenPatterns`); propose entries that match this repo's linters and rules, and the `settings.json` hook wiring from the template.
  - `project/rules/_TEMPLATE.md`: propose a rule file only for an area where an agent would otherwise get something wrong.
  - `factory.json` also carries `mainBranch` and `docsDir` for `/sync-docs`.

## 3b. Make the copied skills project-specific

Each copied skill (`brainstorm`, `root-cause`, `tdd`, `sync-docs`, `verify`) starts with a `## Project facts` block of `<placeholders>`. Fill every placeholder from what step 2 found, with real paths and commands from this repo, not generic wording:
- `root-cause`: log file and the grep that isolates one request; the tables or files that record requests; single-test and suite commands; what counts as sensitive data here.
- `tdd`: which areas have a runner; test folders and how they mirror the source; single-file and suite commands with the folder to run from; test style; the rules a change most often breaks.
- `brainstorm`: the docs to read first; the request path / layering; final check commands per area; the non-negotiable rules.
- `sync-docs`: main branch; docs folder; the CLAUDE.md files; command/tooling config files; other agent docs.
- `verify`: launch command and ready line, smoke check, the steps to reach a change, where to look, cleanup.

Show each filled skill as a diff against the copy, write it on approval. Report any placeholder you could not fill, and leave it as `<…>` rather than inventing a value; a skill with unfilled facts says so on its first line, so the user sees it.

Show everything, then ask for approval per file. Write only what is approved. Nothing else changes.

## 4. Finish

Summarize what exists now, what was proposed but declined, and the first suggested `/factory` or `/quickfix` task to validate the setup on something small.
