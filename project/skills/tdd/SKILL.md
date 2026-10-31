---
name: tdd
description: Build a change test-first — write a failing test, make it pass with minimal code, then tidy up, using this project's test runner and layout.
argument-hint: "[behavior to implement or bug to fix]"
disable-model-invocation: true
---

# Test-driven change

Behavior: $ARGUMENTS

## Project facts
<!-- filled by /onboard from the repo; a line still holding <…> means onboarding did not finish -->
- Areas with a test runner: <e.g. backend only; frontend has none yet>
- Tests live in: <folders, and how they mirror the source layout>
- Run one file: <command, run from which folder>
- Run the suite: <command>
- Test style here: <framework, fixtures, naming, async conventions>
- Project rules that shape the code: <the two or three rules a new change most often breaks>

If the area has no test runner, say so and stop: propose the tool and its install command, do not install it.

1. **Plan the test.** State in one or two lines what the test proves. Check with the user first if the expected behavior is ambiguous.
2. **Red.** Write the test in the layout above, run it with the single-file command, and confirm it fails for the expected reason — not an import error or a typo.
3. **Green.** Write the minimal code that passes, following the project rules above. Run the test, then the suite.
4. **Refactor.** Tidy names and duplication while the tests stay green. Run the suite again.
5. **Report** with fresh test output. Don't commit — the user commits.
