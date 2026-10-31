---
name: brainstorm
description: Take a new feature from idea to approved spec and plan — compare approaches, then write the spec and plan files, stop for approval, and implement only after it. Lighter than /factory; no sub-agents.
argument-hint: "[what to build or change]"
disable-model-invocation: true
---

# Brainstorm → spec → plan → build

Topic: $ARGUMENTS

## Project facts
<!-- filled by /onboard from the repo; a line still holding <…> means onboarding did not finish -->
- Read first: <the CLAUDE.md files, rules folder and docs pages that describe this project's architecture>
- Request path / layering: <e.g. route → controller → feature → repository, or component → store → API>
- Final checks for any change: <test, lint, type-check commands, one per area>
- Things this project never does: <the two or three non-negotiable rules>

Planning files go to `docs/planning/specs/` and `docs/planning/plans/`.

1. **Understand first.** Read the sources above and the relevant code. Note what the change can reuse.
2. **Clarify the goal.** If something essential is unclear, ask — at most 3 short questions in one message. Skip when the goal is clear.
3. **Propose 2–3 approaches.** For each: how it works in a few plain lines, what it touches (files, tables, endpoints), the trade-offs. Prefer the standard, state-of-the-art approach and the project's layering.
4. **Recommend one**, say why, and **stop** for the user's choice. No files yet.
5. **Write both files** once the user has chosen. Same name in both folders: `YYYY-MM-DD-<feature-slug>.md`.
   - `docs/planning/specs/<name>`: Goal · Chosen approach (and why; rejected options one line each) · Behavior, including errors and edge cases · Touches (files, tables, endpoints, migrations) · Out of scope · Done when.
   - `docs/planning/plans/<name>`: first lines `Spec: ../specs/<name>` and `Status: draft`. Then numbered tasks as `- [ ] 1. <change>`, each with **Files:** and **Check:** (the test or command that proves it). End with the final checks listed above. One task = one change a reviewer checks in a minute; no full code listings.
6. **Stop for approval.** Give both paths and a 3-line summary of each. If the user asks for changes, update the files and stop again.
7. **Build after approval.** Set `Status: approved`, then work task by task: make the change, run its check, tick its box. Stop and ask if a task turns out wrong. When all are done, set `Status: done` and report with fresh test output. Don't commit — the user commits.

A later session continues with "continue `docs/planning/plans/<name>`": read the spec and plan, then resume at the first unticked task.

Keep it short and plain; use an analogy when a trade-off is abstract.
