---
name: sync-docs
description: Keep CLAUDE.md files, .claude/rules and the project's docs folder in step with the main branch. Diffs the main branch since the last sync, finds the docs covering the changed files, checks their claims against the branch's code, and proposes edits for approval.
argument-hint: "[since-commit]"
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(git fetch *), Bash(git log *), Bash(git diff *), Bash(git show *), Bash(git grep *), Bash(git rev-parse *), Bash(git branch -r), Bash(cat *)
---

# Sync agent docs with the main branch

## Project facts
<!-- set by /sync-docs on its first run (step 0); a bullet still holding an angle-bracket placeholder triggers that setup -->
- Main branch: <e.g. origin/develop — the branch the docs describe>
- Docs folder: <e.g. docs/wiki; pages carry a `covers:` frontmatter listing the files they describe>
- CLAUDE.md files: <root plus per-area files, e.g. backend/CLAUDE.md, frontend/CLAUDE.md>
- Command/tooling config files: <e.g. requirements.txt, package.json, alembic.ini — when these change, check the Commands section>
- Other agent docs: <e.g. AGENTS.md, or "none">

Last synced commit: !`cat docs/wiki/.last-sync 2>/dev/null || cat docs/.last-sync 2>/dev/null || echo "none"`
Start commit override (optional): $ARGUMENTS

Check every claim against the main branch, never the working tree — it may be a feature branch.

## 0. First run

Skip this step when none of the five bullets under `## Project facts` still holds an angle-bracket placeholder (`<e.g. …>`). Otherwise fill only those bullets; leave filled bullets as they are.

1. Main branch: `git rev-parse --abbrev-ref origin/HEAD` and `git branch -r`. If `origin/develop` exists alongside the branch `origin/HEAD` points to, or `origin/HEAD` does not resolve, ask the user which branch the docs describe; never guess. Store it with the remote prefix, e.g. `origin/develop`.
2. Docs folder: `docs/wiki` if it exists, else `docs`; if neither exists, write `none` (the marker then goes to `docs/.last-sync`, which the header reads).
3. CLAUDE.md files (Glob `**/CLAUDE.md`), command/tooling config files (e.g. `package.json`, `requirements*.txt`, `pyproject.toml`, `alembic.ini`, `Makefile`), other agent docs (e.g. `AGENTS.md`, or `none`).
4. Show the filled block as a diff. If there is no override and no last synced commit, ask for the start commit in the same message. Write the block into this file only after the user approves; if they decline, write nothing and stop. Then continue with step 1.

## 1. Find what changed

If the Main branch fact has no `origin/` prefix (an older setup), read it as `origin/<value>` everywhere below.

1. `git fetch origin <main branch without the origin/ prefix>` (e.g. `git fetch origin develop`).
2. Base = the override if given, else the last synced commit, else the start commit agreed in step 0. If none exists, stop and ask the user for a start commit.
3. Run `git log --first-parent --oneline <base>..<main branch>` and `git diff --name-status <base>..<main branch>`. If nothing changed, say "docs are up to date" and stop.

## 2. Map changed files to docs

- `.claude/rules/*.md`: every rule whose `paths:` frontmatter matches a changed file, plus any rule whose `paths:` name a renamed or deleted file.
- The CLAUDE.md files above: the nearest one for each changed file. The root one: check **Commands** when a command/tooling config file changed; check architecture and rules sections for new tables, migrations, auth or security changes.
- Docs folder pages: every page whose `covers:` matches a changed file, plus any page whose `covers:` names a renamed or deleted file. Update the page table in the folder's README if a page is added or removed.
- Other agent docs only when commands or tooling changed.

Show the mapping (doc ← changed files ← commits) before going further.

## 3. Check each doc against the branch

For each mapped doc, read `git diff <base>..<main branch> -- <its files>`. Then verify every name, path, endpoint, setting, constant and number the doc states about those files, with `git grep -n <name> <main branch> -- <dir>` or `git show <main branch>:<file>`.

Sort each finding:
- **Stale fact** (renamed, removed, changed value) → rewrite the line.
- **New behavior an agent would get wrong without being told** → add one gotcha line to the narrowest doc that loads for those files (a matching rule, else the folder's CLAUDE.md). Test: would missing this make Claude do the wrong thing?
- **The why or history behind a change** → the matching docs page, not CLAUDE.md.
- **Descriptions the code already shows** (file lists, what a function does) → don't add.
- **A new narrow area with no rule** → propose a new rule file; don't create it without approval.

## 4. Propose, then stop

Show one unified diff per file, each hunk tagged with the commit that caused it. Change nothing until the user approves; they may approve hunks one by one.

Style for edits: match the file's terse style; name the source of a value (setting, constant) instead of copying the value; no "now", "no longer" or "used to"; no capitals for emphasis; keep each CLAUDE.md under 200 lines and warn if an edit would cross it.

## 5. After approval

1. Apply exactly the approved hunks.
2. Grep the docs for each old name you replaced and report any leftovers.
3. Write the full `git rev-parse <main branch>` into `<docs folder>/.last-sync` (`docs/.last-sync` when the docs folder is `none`) and tell the user the new marker.

Never commit or push from this skill; the user decides whether these files are tracked.
