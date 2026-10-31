Spec: ../specs/YYYY-MM-DD-<slug>.md
Status: draft
<!-- draft → approved → in-progress → done | incomplete | blocked -->

# Plan: <feature name>

## Tasks
- [ ] 1. <one change a reviewer checks in a minute>
  **Files:** path/a.py, path/b.tsx
  **Check:** <the one command that proves it>
- [ ] 2. …

## Authorized implementation checks
Only these exact commands may run during Stage 2. Approved at Gate 1.
- `cd backend && .venv/bin/python -m pytest tests/<focused file> -q`
- `cd frontend && npx tsc --noEmit -p tsconfig.app.json`

## Approvals
| Gate | Date | User's words (quoted) | Authorizes |
|---|---|---|---|
| 1 plan | | | plan + the checks above |
| 2 implement → test | | | running Stage 3 |
| 3 fix / review / stop | | | exactly what was named |
| 4 review fixes | | | fixes only, unless bundle named |
| stop after review | | | — (record of the verdict) |
| commit | | | one commit |
| push | | | one push |

## Stage log
- Stage 2: tasks done/partial/blocked, checks run → results, new edge cases added to spec rows #…
- Stage 3: executed … / proposed-not-executed … / findings …
- Stage 4: cycle 1 verdict …, cycle 2 verdict …, final verification …

## Review
Angela's findings, each with resolution (fixed in cycle n / accepted by user on date / open).

## Completion report
(filled from completion-report.md at Stage 5)
