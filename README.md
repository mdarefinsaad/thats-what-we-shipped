# That's What We Shipped

A reusable, gated, cost-conscious software-development workflow for Claude Code. One orchestrator (Michael, your main session) and five sub-agents named after The Office (US). Works in any repo once installed; project specifics live in each repo.

```
Michael (you + main session, opus)   plans, gates, explains, writes planning files
  ├─ pam-explorer     sonnet   finds files and flows, read-only, no Bash
  ├─ jim-architect    opus     design options + edge-case matrix, read-only, no Bash
  ├─ darryl-implementer opus   edits approved paths, runs only authorized checks
  ├─ dwight-tester    sonnet   edits test paths only, runs test/lint runners
  └─ angela-reviewer  opus     reviews the diff, read-only + check commands
```

## Install, update, remove

```bash
cd ~/arefin/thats-what-we-shipped
python3 -m unittest discover -s tests -q   # all guards must pass first
python3 install.py --dry-run                   # show what would change
python3 install.py                             # copy into ~/.claude, merge settings
python3 install.py --check                     # drift between repo and ~/.claude
python3 install.py --uninstall                 # remove installed files, restore backups
```

What install does: copies `agents/`, `skills/`, `hooks/` and `CLAUDE.md` into `~/.claude/`; backs up `~/.claude/settings.json` to `settings.json.pre-factory` (first time only) and merges `settings.fragment.json` into it; writes `~/.claude/.factory-manifest.json` listing every file it owns. Uninstall removes exactly those files and restores the backups. The repo itself is versioned with git, so `git log` is the change history and `git checkout <rev> && python3 install.py` is the rollback to any earlier version.

Edit the repo, never `~/.claude/` directly: installed copies are overwritten on the next install, and the global ask rule prompts before any agent touches them.

Per-project skills and hooks live under `project/` and are installed differently; see the section below.

## Daily use

| Situation | Type |
|---|---|
| New repo you have not used the factory in | `/onboard` |
| Empty folder, new product | `/newproject <one-line idea>` |
| Feature or non-trivial change | `/factory <request>` |
| Small, well-understood fix | `/quickfix <symptom>` |
| Unfinished plan from an earlier session | `continue docs/planning/plans/<name>.md` |
| Inside a repo, after `/onboard` | `/brainstorm`, `/root-cause`, `/tdd`, `/sync-docs`, `/verify` (see next section) |
| Commit / push / PR / migration / deploy | ask for it explicitly; it is never part of a stage |

The gates, in order: plan (quotes the authorized implementation checks) → implementation → tests → review → stop. After tests and after review you decide: fix, continue, or stop. "Fix" approves edits only; say "fix, test and re-review" to bundle. Two review-fix cycles maximum, then a final verification with no edits.

Monitoring: terminal output, the statusline, the plan file's ticks and Approvals table, and a macOS banner when a turn finishes, fails, or needs you.

## Per-project skills and hooks (the `project/` kit)

Global skills are installed once and behave the same everywhere. The kit is different: it is copied **into a repo** and then made specific to that repo by `/onboard`.

```
project/skills/   → <repo>/.claude/skills/
project/hooks/    → <repo>/.claude/hooks/
project/rules/    → <repo>/.claude/rules/
```

```bash
python3 install.py --project ~/path/to/repo            # copy; keeps files that already exist
python3 install.py --project ~/path/to/repo --force    # copy; overwrites them
```

Then run `/onboard` in that repo. Every kit skill opens with a `## Project facts` block of `<placeholders>`; `/onboard` inspects the repo, fills them with real paths and commands, shows the diff, and writes on approval. A placeholder it cannot fill stays as `<…>` and is reported, never invented. The exception is `/sync-docs`: `/onboard` leaves its facts blank, and it fills them itself on its first run.

| Skill | What it does | What `/onboard` fills in |
|---|---|---|
| `/brainstorm <idea>` | Idea → 2–3 approaches → spec + plan files → approval → build. Lighter than `/factory`, no sub-agents | docs to read first, request path / layering, final check commands, non-negotiable rules |
| `/root-cause <symptom>` | Reproduce, gather evidence, confirm the earliest point of failure, explain plainly, stop before fixing | log file and the grep for one request, tables that record requests, single-test and suite commands, what counts as sensitive data |
| `/tdd <behavior>` | Red → green → refactor with the project's runner; stops if the area has no runner | areas with a runner, test folders and layout, single-file and suite commands, test style, rules a change most often breaks |
| `/sync-docs [since]` | Diff the main branch since the last sync, map changed files to CLAUDE.md, rules and docs pages, propose edits for approval | nothing — `/sync-docs` sets its own facts (main branch, docs folder, CLAUDE.md files, config files) on its first run |
| `/verify` | How to launch the app and drive it to see a change working | launch command and ready line, smoke check, steps to reach a change, where to look, cleanup |

Hooks in the kit are generic scripts driven by the repo's `.claude/factory.json` (template: `skills/onboard/templates/factory.json`):

| Hook | Event | Config key | Behaviour |
|---|---|---|---|
| `lint_changed_file.py` | PostToolUse Edit/Write | `lintOnEdit`: glob, cwd, command with `{file}` / `{venv}` | runs the matching linter or formatter on the edited file; non-zero output goes back to Claude |
| `forbidden_patterns.py` | PreToolUse Edit/Write | `forbiddenPatterns`: glob, regex, message | blocks an edit that would **add** a forbidden construct; existing violations never block |

`factory.json` also carries `testPaths` and `approvedChecks` for the global guards. `skills/onboard/templates/settings.json` shows the hook wiring. `project/rules/_TEMPLATE.md` shows the `paths:` frontmatter for a path-scoped rule. Tests: `tests/test_project_hooks.py`, `tests/test_skill_headers.py` (no `$(…)` in skill header commands).

Refreshing a repo after the generic kit improves: `install.py --project <repo> --force`, then `/onboard` again. Filled-in, project-specific copies do not belong in this repo; keep them in a backup repo next to the project.

## Model policy

| Who | Default | Override you can ask for | Why |
|---|---|---|---|
| Michael | opus | `/model fable` for an unusually hard session | holds all context, explains, decides |
| Pam | sonnet | haiku for a narrow lookup; if thin, rerun once on sonnet | high read volume, low ambiguity |
| Jim | opus | fable for unusually difficult or high-risk design | design mistakes cost the most |
| Darryl | opus | none | implementation quality |
| Dwight | sonnet | haiku to just run approved checks; opus for concurrency or migration tests | test design is mid-complexity |
| Angela | opus | fable for high-risk or after a critical finding | independence plus strength |

Model choice is per agent file (`model:`), overridable per call by Michael. There is no automatic routing. Billing assumption: on a Team subscription, model choice changes how fast the usage window is consumed and how much metered extra usage is bought; Anthropic publishes no per-model weighting, so "sonnet is cheaper" is a reasonable assumption, not a measured fact. Token waste is avoided by: compact handoffs (paths, not transcripts), the plan file as shared memory, no re-exploration after Pam, no review when nothing changed, and hard caps (`maxTurns`, no nested agents).

## What is enforced vs. what is instructed

Enforced by Claude Code and the guards (works regardless of model or prompt):

- Secret files denied globally (`settings.fragment.json`): `.env*` except `*.example|sample|template`, key files, cloud credentials, `~/.ssh`, `~/.aws`, etc. Read deny rules also cover `cat`, `head`, `sed`, `tail` and shell redirections.
- Ask rules prompt even in auto mode: commit, push, merge, rebase, reset, tag, alembic upgrade/downgrade/stamp, docker push/compose up, kubectl apply/delete, terraform apply/destroy, ssh/scp/rsync, gcloud deploy, gh pr create/merge, gh release, and any edit under `~/.claude/` factory paths or a project's `.claude/`.
- `hooks/bash_policy.py` (global, every session and sub-agent): applies the same secret deny and consequential-command ask to the **real** command after looking through the RTK wrapper. Needed because RTK rewrites `cat .env` to `rtk read .env` and `git commit` to `rtk git commit` before Claude Code evaluates rules, which the demonstration showed bypasses both the `Read(.env*)` deny and the `Bash(git commit *)` ask rule. Any other wrapper hook you add later needs the same treatment.
- Pam and Jim: no Bash tool, no edit tools. Angela: no edit tools.
- `hooks/bash_guard.py` (Angela, Dwight, Darryl): allowlist of read-only commands, read-only git, and test/lint runners; Darryl additionally limited to the exact `authorized_checks` in `docs/planning/active-scope.json`. Blocks redirections, command substitution, shells, inline interpreters, `sed -i`, `rm/mv/cp/tee`, git writes, installs, deploy tools, background jobs, subshells, here-docs. Fails closed.
- `hooks/edit_scope.py` (Darryl, Dwight): Darryl edits only `approved_paths`; Dwight only test paths (scope file → `.claude/factory.json` `testPaths` → generic defaults). Both blocked on `.claude/`, `docs/planning/`, `~/.claude/`, outside the project. No scope file = no edits.
- No agent can spawn agents; each has a turn cap.

Instructed only (prompt text, not a wall):

- Michael's stage order, gate wording, approvals logging, cycle limits, report format.
- Darryl running only authorized checks **as the orchestrator intends**: the guard enforces the exact strings; what the strings are is a human decision at gate 1.
- Dwight writing meaningful tests; Angela's thoroughness.

Known limits, stated plainly:

- The Bash guard matches command text. An allowed runner (`pytest`, `npm test`) can still write files via its own subprocesses, and tests legitimately write caches (`.pytest_cache`, `__pycache__`, coverage files). Only Claude Code's sandbox blocks at the OS level; it is not enabled by this setup. Enable it later via `/sandbox` or the `sandbox` settings key once you have checked it does not break the project's hooks.
- Read deny rules do not catch a script that opens a secret file by itself (a Python test reading `.env`). Same answer: sandbox.
- Frontmatter hooks on agents are documented; the install demonstration verifies they fire on this machine. If a future Claude Code version changes that, move the same hook entries into `settings.fragment.json` under `PreToolUse` with an agent-type matcher.

## Layers: what lives where

| Layer | Location | Holds | Scope |
|---|---|---|---|
| Global foundation | `~/.claude/` (from this repo) | CLAUDE.md working rules, agents, skills, hooks, deny/ask rules, notifications | every project on this Mac |
| Project | `<repo>/CLAUDE.md`, `<repo>/.claude/` | architecture, commands, project rules, project secrets, lint hooks, `factory.json` (test paths, extra approved checks) | that repo |
| Task | `<repo>/docs/planning/` | spec with edge-case matrix, plan with approvals, `active-scope.json` | one piece of work |

Precedence facts (verified in the docs): deny rules are evaluated first and lists merge across scopes, so a project cannot loosen a global deny. A project agent with the same name replaces a global one, which is why safety lives in settings and hooks, not in agent prompts. `defaultMode: auto` or `bypassPermissions` only work from user or managed settings, never from a project file. `~/.claude/skills`, `~/.claude/agents` and `~/.claude/rules` apply to all projects automatically; project files add to them.

Leak prevention: nothing project-specific goes into this repo. Project names, paths, commands and secrets belong in the project's own `CLAUDE.md`, `.claude/settings.json` and `.claude/factory.json`. Sub-agents load the project's CLAUDE.md automatically, which is how they learn its conventions.

## Workflows at a glance

**Small bug fix** (`/quickfix`): locate → verified cause → short checklist → Gate A (plan + authorized checks) → fix → Gate B → tests → Gate C → Angela → fixes only on approval, ≤2 cycles → final verification → report.

**Full-stack feature** (`/factory`): triage → Pam → Jim if a design decision → questions to you → spec + plan + scope → Gate 1 → Darryl → Gate 2 → Dwight → Gate 3 → Angela → Gate 4 (≤2 cycles) → final verification → report → separate commit request.

**High-risk change** (auth, migration, payments, deletion, external comms): same as feature, plus Jim mandatory, Angela on fable, each risky action its own plan item and its own approval, ask rules prompt before migration or deploy commands, rollback noted in the spec.

## Validation checklist (run after install)

1. Guards: `python3 -m unittest discover -s tests -q` → OK.
2. Agents visible: in a new session ask Michael to list available agent types; the five names appear.
3. Model per agent: run Pam on a lookup; the task notification shows the sonnet model id.
4. Secrets: in a demo repo with `.env` and `.env.example`, `cat .env` is denied, `cat .env.example` is allowed.
5. Angela cannot write: ask her to run `echo x > /tmp/f`, `sed -i`, `cat a && rm b`, `python -c` → all blocked by bash_guard.
6. Dwight scope: ask him to edit a production file → blocked; a test file → allowed.
7. Darryl scope: without `active-scope.json` every edit is blocked; with it, only approved paths and only authorized checks.
8. Ask rule: `git commit --dry-run` prompts even in auto mode.
9. Notification: a banner appears when a turn ends.
10. End to end: `/quickfix` on a real small task, then `/factory` on a real feature.

## Maintenance

- Change a guard: edit in `hooks/`, add a test case, run the tests, `python3 install.py`, commit.
- Change an agent or skill: edit in the repo, `python3 install.py`, try it on a demo repo, commit.
- `python3 install.py --check` shows drift if something in `~/.claude/` was edited by hand.
- A newer Claude Code may add or rename fields; the authoritative list is https://code.claude.com/docs/en/sub-agents and /skills and /settings. Unknown frontmatter fields are ignored silently, so re-verify after major upgrades.
