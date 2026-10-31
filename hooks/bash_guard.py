#!/usr/bin/env python3
"""PreToolUse guard for Bash, attached per agent in its frontmatter.

Usage (in agent frontmatter):
    python3 -I "$HOME/.claude/hooks/bash_guard.py" --role reviewer|tester|implementer

What it enforces
  reviewer / tester : only read-only commands, read-only git, and test/lint
                      runners, plus project-approved checks listed in
                      .claude/factory.json under "approvedChecks".
  implementer       : only read-only commands, read-only git, and the exact
                      commands listed under "authorized_checks" in
                      docs/planning/active-scope.json (written by the
                      orchestrator at gate 1). Missing scope file = only
                      read-only commands.
  everyone          : no redirections, no command substitution, no shells,
                      no interpreters with inline code, no file-changing
                      tools (rm, mv, cp, tee, sed -i, ...), no git writes,
                      no package installs, no deploy tools.

What it does NOT enforce (documented limit)
  A command that is allowed (pytest, npm test, ...) can still write files
  through its own subprocesses. Only the Claude Code sandbox blocks that at
  OS level. This guard is policy enforcement by command matching.

Exit codes: 0 = no opinion (the normal permission flow continues),
            2 = blocked, with the reason on stderr for the agent to read.
"""

import json
import os
import re
import shlex
import sys

ROLES = ("reviewer", "tester", "implementer")

# Commands whose only job is to look at things.
READ_ONLY_COMMANDS = {
    "cat", "head", "tail", "less", "more", "wc", "ls", "tree", "pwd", "echo",
    "printf", "which", "stat", "file", "cd", "true", "sort", "uniq", "cut",
    "tr", "jq", "date", "diff", "grep", "rg", "basename", "dirname", "realpath",
    "type", "column", "nl", "shasum", "sha256sum",
}

GIT_READ_ONLY = {
    "diff", "log", "show", "status", "grep", "blame", "rev-parse", "ls-files",
    "shortlog", "describe", "branch", "remote", "tag", "worktree", "stash",
    "config", "cat-file", "name-rev", "merge-base", "diff-tree", "ls-tree",
}

GIT_BRANCH_MODIFYING_FLAGS = {
    "-d", "-D", "-m", "-M", "-c", "-C", "--delete", "--move", "--copy",
    "-f", "--force", "-u", "--set-upstream-to", "--unset-upstream",
}

ALEMBIC_READ_ONLY = {"heads", "current", "history", "check", "branches", "show"}

FIND_MODIFYING_FLAGS = {"-delete", "-exec", "-execdir", "-ok", "-okdir"}

ALLOWED_NPM_SCRIPTS = re.compile(r"^(lint|test|tests|typecheck|type-check|check|coverage)(:.*)?$")

NOT_APPROVED = "not on the approved command list for this role"


def fail(reason: str, command: str) -> None:
    sys.stderr.write(f"bash_guard: blocked `{command}`: {reason}\n")
    sys.exit(2)


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def normalize(command: str) -> str:
    return " ".join(command.split())


def strip_harmless_redirects(command: str) -> str:
    """Drop stderr-to-stdout and to-/dev/null redirects: they read and write nothing."""
    command = re.sub(r"\s*2>&1", "", command)
    command = re.sub(r"\s*[12]?>\s*/dev/null", "", command)
    command = re.sub(r"\s*&>\s*/dev/null", "", command)
    return command


def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def split_segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = [[]]
    for tok in tokens:
        if tok in ("&&", "||", "|", ";"):
            segments.append([])
        else:
            segments[-1].append(tok)
    return [seg for seg in segments if seg]


def strip_rtk(seg: list[str]) -> list[str]:
    """`rtk <cmd>` and `rtk proxy <cmd>` wrap a command to save tokens; judge the wrapped command."""
    if seg and seg[0] == "rtk":
        return seg[2:] if len(seg) > 1 and seg[1] == "proxy" else seg[1:]
    return seg


def is_python(name: str) -> bool:
    return re.fullmatch(r"python(3(\.\d+)?)?", name) is not None


def git_reason(args: list[str]) -> str | None:
    if not args:
        return "bare git"
    sub, rest = args[0], args[1:]
    if sub not in GIT_READ_ONLY:
        return f"git {sub} can change the repository"
    if any(a.startswith("--output") for a in rest):
        return "git --output writes a file"
    if sub == "branch":
        if any(a in GIT_BRANCH_MODIFYING_FLAGS for a in rest):
            return "git branch with a modifying flag"
        if any(not a.startswith("-") for a in rest):
            return "git branch <name> creates a branch"
    if sub == "tag" and any(not a.startswith("-") for a in rest):
        return "git tag <name> creates a tag"
    if sub == "remote" and rest and rest[0] not in ("-v", "show", "get-url"):
        return "git remote can change remotes"
    if sub == "worktree" and rest[:1] != ["list"]:
        return "git worktree is allowed only as `git worktree list`"
    if sub == "stash" and rest[:1] not in (["list"], ["show"]):
        return "git stash is allowed only as list/show"
    if sub == "config" and not (rest and rest[0] in ("--get", "--list", "-l", "--get-all")):
        return "git config is allowed only as --get/--list"
    return None


def ruff_reason(args: list[str]) -> str | None:
    if "--fix" in args or "--unsafe-fixes" in args:
        return "ruff --fix edits files"
    if args[:1] == ["format"] and not ("--check" in args or "--diff" in args):
        return "ruff format without --check rewrites files"
    return None


def npx_reason(args: list[str]) -> str | None:
    if not args:
        return "bare npx"
    tool, targs = args[0], args[1:]
    if tool == "tsc":
        return None if "--noEmit" in targs else "tsc without --noEmit writes output"
    if tool == "eslint":
        return "eslint --fix edits files" if "--fix" in targs else None
    if tool == "vitest":
        return None if ("run" in targs or "--run" in targs) else "vitest is allowed only as `vitest run`"
    if tool == "prettier":
        return None if ("--check" in targs or "-c" in targs) else "prettier without --check rewrites files"
    if tool in ("jest", "playwright"):
        return None
    return f"npx {tool} is not on the approved list"


def runner_reason(name: str, args: list[str]) -> str | None:
    """Test and lint runners, allowed for reviewer and tester only."""
    if name == "pytest":
        return None
    if is_python(name):
        if args[:2] == ["-m", "ruff"]:
            return ruff_reason(args[2:])
        if args[:2] in (["-m", "pytest"], ["-m", "unittest"], ["-m", "mypy"], ["-m", "pyright"]):
            return None
        return "python is allowed only as `python -m pytest|unittest|mypy|pyright|ruff`"
    if name == "ruff":
        return ruff_reason(args)
    if name in ("mypy", "pyright", "flake8", "pylint", "bandit"):
        return None
    if name == "black":
        return None if ("--check" in args or "--diff" in args) else "black without --check reformats files"
    if name == "alembic":
        return None if (args and args[0] in ALEMBIC_READ_ONLY) else "alembic can change the database"
    if name == "npm":
        if args[:1] in (["test"], ["t"], ["ls"], ["view"], ["outdated"], ["audit"]):
            return None
        if args[:1] == ["run"] and len(args) > 1 and ALLOWED_NPM_SCRIPTS.match(args[1]):
            return None
        return "npm is allowed only as `npm test`, `npm run lint|test|typecheck|check|coverage`"
    if name in ("pnpm", "yarn"):
        if args[:1] == ["test"] or (args[:1] == ["run"] and len(args) > 1 and ALLOWED_NPM_SCRIPTS.match(args[1])):
            return None
        return f"{name} is allowed only for test/lint/typecheck scripts"
    if name == "npx":
        return npx_reason(args)
    if name == "cargo" and args[:1] and args[0] in ("test", "check", "clippy"):
        return None
    if name == "cargo" and args[:1] == ["fmt"] and "--check" in args:
        return None
    if name == "go" and args[:1] and args[0] in ("test", "vet"):
        return None
    return NOT_APPROVED


def segment_reason(seg: list[str], role: str, project_checks: list[str]) -> str | None:
    """None if the segment is allowed for this role, otherwise why not."""
    seg = strip_rtk(seg)
    while seg and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", seg[0]):
        seg = seg[1:]  # leading VAR=value assignments are harmless
    if not seg:
        return None
    name = os.path.basename(seg[0])
    args = seg[1:]

    joined = " ".join(seg)
    if role in ("reviewer", "tester") and any(joined == c or joined.startswith(c + " ") for c in project_checks):
        return None

    if name in READ_ONLY_COMMANDS:
        return None
    if name == "find":
        return "find with -delete/-exec is not read-only" if any(a in FIND_MODIFYING_FLAGS for a in args) else None
    if name == "sed":
        if any(a.startswith("-i") for a in args):
            return "sed -i edits files in place"
        if "-n" not in args or not any(re.fullmatch(r"\d+(,\d+)?p", a) for a in args):
            return "sed is allowed only as `sed -n <range>p <file>`"
        return None
    if name == "git":
        return git_reason(args)
    if role == "implementer":
        return NOT_APPROVED
    return runner_reason(name, args)


def main() -> None:
    argv = sys.argv[1:]
    role = argv[1] if len(argv) == 2 and argv[0] == "--role" and argv[1] in ROLES else None
    if role is None:
        sys.stderr.write("bash_guard: usage --role reviewer|tester|implementer\n")
        sys.exit(2)

    try:
        payload = json.load(sys.stdin)
    except ValueError:
        fail("hook input was not JSON", "?")
    if payload.get("tool_name") != "Bash":
        sys.exit(0)
    command = payload.get("tool_input", {}).get("command")
    if not isinstance(command, str) or not command.strip():
        fail("empty command", "")

    original = normalize(command)
    if "`" in original or "$(" in original or "<(" in original or ">(" in original:
        fail("command substitution / process substitution is not allowed", original)

    cleaned = strip_harmless_redirects(command.replace("\n", " ; "))
    if re.search(r"(^|[^&])[<>]", cleaned):
        fail("redirections are not allowed (except 2>&1 and >/dev/null)", original)

    try:
        tokens = tokenize(cleaned)
    except ValueError as exc:
        fail(f"could not parse command safely ({exc})", original)
    if any(t in ("&", "(", ")", "<<", ">>", ">&", "<&") for t in tokens):
        fail("background jobs, subshells and here-docs are not allowed", original)

    project = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    scope = load_json(os.path.join(project, "docs", "planning", "active-scope.json"))
    factory_cfg = load_json(os.path.join(project, ".claude", "factory.json"))
    project_checks = [normalize(c) for c in factory_cfg.get("approvedChecks", []) if isinstance(c, str)]

    if role == "implementer":
        authorized = [normalize(c) for c in scope.get("authorized_checks", []) if isinstance(c, str)]
        candidate = normalize(cleaned)
        if candidate in authorized or (candidate.startswith("rtk ") and normalize(candidate[4:]) in authorized):
            sys.exit(0)  # the whole command is one of the checks the user authorized at gate 1

    for seg in split_segments(tokens):
        reason = segment_reason(seg, role, project_checks)
        if reason is None:
            continue
        if role == "implementer" and reason == NOT_APPROVED:
            if not scope:
                reason = ("no docs/planning/active-scope.json; the orchestrator writes it at gate 1, "
                          "until then only read-only commands are allowed")
            else:
                reason = "not an authorized check from docs/planning/active-scope.json and not read-only"
        fail(reason, original)

    sys.exit(0)


if __name__ == "__main__":
    main()
