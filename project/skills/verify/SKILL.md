---
name: verify
description: How to launch this project's app and drive it to observe a change at runtime. Filled in by /onboard from the project's own run instructions.
---

# Verifying <project> changes at runtime

<!-- filled by /onboard from the repo; a line still holding <…> means onboarding did not finish. Delete sections that do not apply. Keep it to what a person needs to see a change working, not a full manual. -->

Surface: <HTTP API | CLI | web UI | worker>. Covers: <which part, e.g. backend only>.

## Launch

```bash
cd <dir>
<exact start command>           # ready when the log says "<ready line>", ~<n> s
```

Prerequisites: <database up / env file / ports>. Never print secret values; refer to variables by name.

## Smoke check

```bash
<one request or command that proves the app is up, e.g. curl -s localhost:<port>/health>
```

## Drive a change

Typical sequence to reach the changed behaviour:

1. <step, with the exact command or request and what to look for in the response>
2. <step>
3. <where the result shows: response field, log line, table row>

## Where to look when it does not work

- Logs: `<path or command>`; filter by `<request id field>`.
- State: `<table or file>`.
- Known traps: <one line each>.

## Clean up

<what the run leaves behind and how to remove it, if anything>
