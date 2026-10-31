#!/usr/bin/env python3
"""Global PreToolUse policy for every Bash call, in every session and sub-agent.

Why it exists
  Permission rules match the command text Claude Code evaluates. A wrapper
  such as RTK rewrites `cat .env` into `rtk read .env` and `git commit` into
  `rtk git commit` before that evaluation, so `Read(.env*)` deny rules and
  `Bash(git commit *)` ask rules no longer match. This hook looks through the
  wrapper and applies the same policy to the real command.

What it does
  deny : any command that names a secret file or folder (.env*, key files,
         cloud credentials, ~/.ssh, ...), templates (*.example, *.sample,
         *.template) excepted.
  ask  : consequential commands (git commit/push/merge/rebase/reset/tag,
         alembic upgrade/downgrade/stamp, docker push / compose up, kubectl
         apply/delete, terraform apply/destroy, ssh/scp/rsync, gcloud deploy,
         gh pr create/merge, gh release) → the user is prompted even in auto
         mode; in a headless run they are denied.
  else : no opinion (exit 0, nothing printed).

Wired in ~/.claude/settings.json by install.py (settings.fragment.json).
"""

import json
import os
import re
import shlex
import sys

SECRET_BASENAMES = re.compile(
    r"^(\.env(\..+)?|.*\.(pem|p12|pfx|jks|keystore)|id_(rsa|ed25519|ecdsa).*"
    r"|.*service[-_]account.*\.json|.*credentials.*\.json|\.npmrc|\.pypirc|\.netrc)$",
    re.I,
)
TEMPLATE_SUFFIX = re.compile(r"\.(example|sample|template)$", re.I)
SECRET_DIRS = ("/.ssh/", "/.aws/", "/.config/gcloud/", "/.kube/", "/secrets/")
SECRET_FILES = ("/.docker/config.json",)

CONSEQUENTIAL = [
    (("git",), {"commit", "push", "merge", "rebase", "reset", "tag"}),
    (("alembic",), {"upgrade", "downgrade", "stamp"}),
    (("docker",), {"push"}),
    (("docker", "compose"), {"up"}),
    (("docker-compose",), {"up"}),
    (("kubectl",), {"apply", "delete"}),
    (("terraform",), {"apply", "destroy"}),
    (("gh", "pr"), {"create", "merge"}),
    (("gh",), {"release"}),
]
ALWAYS_ASK = {"ssh", "scp", "rsync"}


def tokens_of(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return command.split()


def segments(command: str) -> list[list[str]]:
    out: list[list[str]] = [[]]
    for tok in tokens_of(command.replace("\n", " ; ")):
        if tok in ("&&", "||", "|", ";"):
            out.append([])
        else:
            out[-1].append(tok)
    return [s for s in out if s]


def unwrap(seg: list[str]) -> list[str]:
    """rtk <cmd> / rtk proxy <cmd> → <cmd>; rtk read <file> → cat <file>."""
    if seg and seg[0] == "rtk":
        if len(seg) > 1 and seg[1] == "proxy":
            return seg[2:]
        if len(seg) > 1 and seg[1] == "read":
            return ["cat"] + seg[2:]
        return seg[1:]
    return seg


def names_secret(token: str) -> bool:
    path = os.path.expanduser(token.strip("'\""))
    if not path or path.startswith("-"):
        return False
    base = os.path.basename(path.rstrip("/"))
    if TEMPLATE_SUFFIX.search(base):
        return False
    if SECRET_BASENAMES.match(base):
        return True
    full = os.path.abspath(path) if path.startswith(("/", "~", ".")) else "/" + path
    return any(d in full + "/" for d in SECRET_DIRS) or any(full.endswith(f) for f in SECRET_FILES)


def is_consequential(seg: list[str]) -> bool:
    if not seg:
        return False
    name = os.path.basename(seg[0])
    if name in ALWAYS_ASK:
        return True
    for prefix, subs in CONSEQUENTIAL:
        if name == prefix[0] and seg[1:len(prefix)] == list(prefix[1:]):
            rest = seg[len(prefix):]
            if rest and rest[0] in subs:
                return True
    if name == "gcloud" and "deploy" in seg[1:]:
        return True
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    if payload.get("tool_name") != "Bash":
        sys.exit(0)
    command = payload.get("tool_input", {}).get("command")
    if not isinstance(command, str) or not command.strip():
        sys.exit(0)

    for raw in segments(command):
        seg = unwrap(raw)
        for tok in seg:
            if names_secret(tok):
                sys.stderr.write(f"bash_policy: blocked, `{tok}` is a secret file or folder (templates *.example/*.sample/*.template are allowed)\n")
                sys.exit(2)
        if is_consequential(seg):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": f"consequential command needs explicit approval: {' '.join(seg[:3])}",
                }
            }))
            sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
