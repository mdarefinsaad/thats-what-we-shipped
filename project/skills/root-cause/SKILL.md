---
name: root-cause
description: Investigate a bug to its verified root cause — reproduce, gather evidence, explain it plainly — without fixing anything until the user asks.
argument-hint: "[symptom or error]"
disable-model-invocation: true
---

# Find the root cause

Symptom: $ARGUMENTS

## Project facts
<!-- filled by /onboard from the repo; a line still holding <…> means onboarding did not finish -->
- Logs: <log file or command, and how to filter one request, e.g. grep "req":<id>>
- Request records: <tables, files or dashboards that record what happened to a request>
- Run one test: <command for a single test file>
- Run the suite: <command for the whole suite of the affected area>
- Sensitive data in this project: <what must never be pasted: user content, images, document numbers, tokens>

1. **Locate it.** Find where it happens: the logs, the request records, a failing test, the code path (all listed above). Write down what actually happens versus what should.
2. **Test hypotheses.** List the likely causes and check each against evidence — code, data, a small experiment. Drop the ones the evidence rules out; don't stop at the first plausible story.
3. **Confirm the root cause** — the earliest point where things go wrong, not where the error shows up. Show the evidence (file:line, log line, query result). If a change caused it, find the commit with `git log` or `git bisect`.
4. **Explain it plainly:** a few lines, one analogy, what's affected and since when.
5. **Stop.** Don't fix. Name the fix options in one line each if useful, and wait for the user to ask.

Never paste the sensitive data named above while investigating.
