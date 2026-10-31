# Edge-case checklist (pick what applies, say what you excluded)

Use per task. Small fix: a few lines. Feature: a matrix in the spec. High-risk: every group considered, exclusions justified.

## Input
- empty, missing, null, whitespace-only
- malformed (wrong type, bad encoding, invalid JSON, broken image)
- duplicate submissions, repeated IDs
- unexpectedly large (file size, list length, string length, deep nesting)
- unexpected characters: unicode, emoji, control chars, path separators, quotes

## Boundaries and values
- exact boundary (0, 1, max, max+1, equal-to-now)
- precision and rounding (money, floats, percentages)
- dates and times: time zone, DST, leap day, end of month, "now" vs stored time, clock skew
- encoding and locale (decimal comma, RTL text, lowercase/uppercase IDs)

## Auth and isolation
- unauthenticated, expired token, token for another user or client
- authorized but for a different tenant or record (IDOR)
- role escalation, admin-only paths, service-to-service calls
- secrets in logs, URLs, error messages

## Concurrency and repetition
- two requests at once on the same record
- retries, double-click, idempotency keys
- out-of-order events, late webhooks
- background task running while the user acts

## Failure paths
- timeout of a dependency (DB, HTTP, cloud API)
- partial failure halfway through a multi-step operation
- process interrupted, container restarted mid-task
- dependency unavailable at startup

## Data and migrations
- transaction boundaries, rollback on error
- migration on existing rows (nulls, defaults, backfill, size)
- backward compatibility of API responses and stored formats
- deleted or archived referenced rows

## UI
- loading, empty, error and recovery states
- slow network, offline, retry
- keyboard navigation, screen reader labels, focus after actions
- small screens, rotation, camera or permission denied
- browser differences that matter to this feature

## Limits and abuse
- rate limits, quotas, memory and disk
- malicious input aimed at parsers, uploads, regexes
- cost blow-up (unbounded loops, N+1 queries, large model calls)
