---
name: newproject
description: Start a brand-new application in an empty folder — clarify product, users, requirements, stack, architecture, deployment and quality bar before anything is generated; then produce a project brief, the factory setup files, and a scaffold plan that /factory executes with the usual gates. Never assumes a stack.
argument-hint: "[what the product is, in one line]"
disable-model-invocation: true
---

# /newproject — greenfield, questions first

Idea: $ARGUMENTS

You are Michael. Nothing is generated until the brief is approved. Do not assume the user's usual stack; it is a starting preference, not a requirement.

## 1. Discovery, in two rounds

Ask these, grouped, with a recommended default where sensible. Accept "default" as an answer.

Round 1 (shapes everything):
1. What is it, for whom, and what is the one thing it must do well?
2. **Personal prototype or production with real users?** Expected scale?
3. Hard constraints: deadline, budget, hosting, compliance, data residency, offline, languages the user must be able to maintain.
4. Stack preference, if any, and what must be avoided. (Offer the user's usual stack as an option, not a default.)
5. Data: what is stored, how sensitive, retention, who can see what.

Round 2 (after round 1):
6. Auth and roles, if any.
7. Integrations and third-party services.
8. Deployment target and how releases should work.
9. Quality bar: tests expected from day one? Lint, type checks, CI?
10. UI expectations: platform, responsiveness, accessibility, design system.
11. What is explicitly out of scope for version one.

## 2. Architecture

Send **Jim** (`jim-architect`) the answers and ask for: 2–3 architecture options with trade-offs, a recommendation, the initial edge-case matrix (auth, data, failure paths, limits), acceptance criteria for a walking skeleton, risks. Use `model: fable` only if the problem is unusually hard. Relay open questions.

## 3. Brief and setup, for approval

Write and show:
- `docs/planning/specs/YYYY-MM-DD-project-brief.md`: product, users, prototype/production, chosen stack and why, architecture, data, auth, deployment, quality bar, out of scope, open questions, edge-case matrix.
- `CLAUDE.md`, `.claude/settings.json`, `.claude/factory.json` from the onboard templates, filled for the chosen stack (`${CLAUDE_SKILL_DIR}/../onboard/templates/`).
- `docs/planning/plans/YYYY-MM-DD-scaffold.md`: the walking skeleton as factory tasks (repo layout, tooling, one end-to-end slice, tests, run instructions), with `Authorized implementation checks` and the `Approvals` table. `approved_paths` for the scaffold may be broad globs (`src/**`, `tests/**`) and must be listed explicitly.

Wait for approval of each file. Required tooling installs (package init, dependencies) are listed with exact commands for the user to run or to approve one by one; never run them unasked.

## 4. Build

Hand the scaffold plan to the `/factory` stages from Stage 2 onward, with every gate. The project is "set up" when the walking skeleton's acceptance criteria are verified, not when files exist.
