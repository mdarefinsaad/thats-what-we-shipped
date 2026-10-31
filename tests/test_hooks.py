"""Tests for the factory guards. Run from the repo root:

    python3 -m unittest -v tests/test_hooks.py

Each test feeds a hook the same JSON Claude Code sends on PreToolUse and
checks the exit code: 0 = allowed (no opinion), 2 = blocked.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks")
BASH_GUARD = os.path.join(HOOKS, "bash_guard.py")
EDIT_SCOPE = os.path.join(HOOKS, "edit_scope.py")

AUTHORIZED = [
    "cd backend && .venv/bin/python -m pytest tests/controllers/test_session.py -q",
    "cd frontend && npx tsc --noEmit -p tsconfig.app.json",
]


def run_hook(script: str, role: str, payload: dict, project: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project)
    return subprocess.run(
        [sys.executable, "-I", script, "--role", role],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )


def bash_payload(command: str, cwd: str) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": cwd,
            "tool_input": {"command": command}}


def edit_payload(path: str, cwd: str, tool: str = "Edit") -> dict:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": cwd, "tool_input": {key: path}}


class ProjectDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = os.path.realpath(self.tmp.name)
        os.makedirs(os.path.join(self.project, "docs", "planning"))
        os.makedirs(os.path.join(self.project, ".claude"))

    def tearDown(self):
        self.tmp.cleanup()

    def write_scope(self, **extra):
        scope = {
            "plan": "docs/planning/plans/2026-10-30-demo.md",
            "approved_paths": ["backend/app/controllers/session_controller.py", "frontend/src/pages/**"],
            "test_paths": ["backend/tests/**", "frontend/src/**/*.test.tsx"],
            "authorized_checks": AUTHORIZED,
        }
        scope.update(extra)
        with open(os.path.join(self.project, "docs", "planning", "active-scope.json"), "w") as fh:
            json.dump(scope, fh)

    def write_factory(self, **cfg):
        with open(os.path.join(self.project, ".claude", "factory.json"), "w") as fh:
            json.dump(cfg, fh)


class BashGuardReviewerAndTester(ProjectDir):
    ALLOWED = [
        "git diff",
        "git diff --stat HEAD~1",
        "git log --oneline -20 | head -5",
        "git status",
        "git branch --show-current",
        "cat src/a.py",
        "head -50 backend/app/main.py",
        "sed -n 1,40p backend/app/main.py",
        "grep -rn 'expiry' backend/app",
        "rg expiry backend/app",
        "ls -la backend/tests",
        "cd backend && .venv/bin/python -m pytest tests -q",
        "cd backend && .venv/bin/python -m pytest tests/controllers/test_session.py -q 2>&1",
        "pytest -q",
        "cd backend && .venv/bin/ruff check app",
        "cd backend && .venv/bin/ruff format --check app",
        "cd frontend && npx tsc --noEmit -p tsconfig.app.json",
        "cd frontend && npm run lint",
        "cd frontend && npm test",
        "cd frontend && npx vitest run",
        "cd frontend && npx eslint src/App.tsx",
        "rtk git status",
        "rtk proxy git diff",
        "PYTHONPATH=. .venv/bin/python -m pytest tests -q",
        "alembic heads",
        "find . -name '*.py' | wc -l",
    ]
    BLOCKED = [
        "echo x > /tmp/f",
        "echo x >> notes.txt",
        "cat < input.txt",
        "sed -i 's/a/b/' src/a.py",
        "sed -i.bak 's/a/b/' src/a.py",
        "cat a && rm b",
        "ls; curl http://example.com",
        "python -c \"open('x','w').write('1')\"",
        "python3 -c 'print(1)'",
        "bash -c 'ls'",
        "sh -c 'ls'",
        "git checkout -- .",
        "git add -A",
        "git commit -m x",
        "git push",
        "git stash",
        "git branch new-branch",
        "git branch -D old",
        "git diff --output=/tmp/d.patch",
        "git worktree add ../x",
        "cd backend && .venv/bin/ruff check --fix app",
        "cd backend && .venv/bin/ruff format app",
        "cd frontend && npx eslint --fix src/App.tsx",
        "cd frontend && npx tsc -p tsconfig.app.json",
        "cd frontend && npm run build",
        "npm install lodash",
        "pip install requests",
        "cat $(echo .env)",
        "cat `echo .env`",
        "find . -name '*.pyc' -delete",
        "find . -name '*.py' -exec rm {} \\;",
        "echo x | tee out.txt",
        "ls | xargs rm",
        "alembic upgrade head",
        "cd backend && .venv/bin/alembic upgrade head",
        "sleep 100 &",
        "(cd /tmp && ls)",
        "cat <<EOF\nhi\nEOF",
        "docker compose up -d",
        "rm -rf build",
        "mv a b",
        "cp a b",
        "chmod +x run.sh",
        "touch newfile",
        "mkdir newdir",
        "make test",
        "env FOO=1 rm x",
        "cat a\nrm b",
    ]

    def test_allowed_for_reviewer_and_tester(self):
        for role in ("reviewer", "tester"):
            for cmd in self.ALLOWED:
                with self.subTest(role=role, cmd=cmd):
                    res = run_hook(BASH_GUARD, role, bash_payload(cmd, self.project), self.project)
                    self.assertEqual(res.returncode, 0, res.stderr)

    def test_blocked_for_reviewer_and_tester(self):
        for role in ("reviewer", "tester"):
            for cmd in self.BLOCKED:
                with self.subTest(role=role, cmd=cmd):
                    res = run_hook(BASH_GUARD, role, bash_payload(cmd, self.project), self.project)
                    self.assertEqual(res.returncode, 2, f"should be blocked: {cmd}")
                    self.assertIn("bash_guard: blocked", res.stderr)

    def test_project_approved_checks_extend_the_list(self):
        cmd = "cd frontend && npm run build"
        res = run_hook(BASH_GUARD, "reviewer", bash_payload(cmd, self.project), self.project)
        self.assertEqual(res.returncode, 2)
        self.write_factory(approvedChecks=["npm run build"])
        res = run_hook(BASH_GUARD, "reviewer", bash_payload(cmd, self.project), self.project)
        self.assertEqual(res.returncode, 0, res.stderr)
        # project checks never unlock the implementer
        self.write_scope()
        res = run_hook(BASH_GUARD, "implementer", bash_payload(cmd, self.project), self.project)
        self.assertEqual(res.returncode, 2)

    def test_non_bash_tools_are_ignored(self):
        payload = {"tool_name": "Read", "tool_input": {"file_path": "x"}, "cwd": self.project}
        res = run_hook(BASH_GUARD, "reviewer", payload, self.project)
        self.assertEqual(res.returncode, 0)

    def test_bad_role_or_input_fails_closed(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project)
        res = subprocess.run([sys.executable, "-I", BASH_GUARD, "--role", "boss"],
                             input="{}", capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 2)
        res = subprocess.run([sys.executable, "-I", BASH_GUARD, "--role", "reviewer"],
                             input="not json", capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 2)


class BashGuardImplementer(ProjectDir):
    def test_only_authorized_checks_and_read_only(self):
        self.write_scope()
        for cmd in AUTHORIZED + ["git diff", "git status", "cat backend/app/main.py",
                                 "rtk " + AUTHORIZED[0], "  cd backend   &&  .venv/bin/python -m pytest tests/controllers/test_session.py -q "]:
            with self.subTest(cmd=cmd):
                res = run_hook(BASH_GUARD, "implementer", bash_payload(cmd, self.project), self.project)
                self.assertEqual(res.returncode, 0, res.stderr)
        for cmd in ["cd backend && .venv/bin/python -m pytest tests -q",   # full suite not authorized
                    "npx tsc --noEmit",                                    # not the exact authorized form
                    "pytest -q",
                    "cd frontend && npm run lint",
                    AUTHORIZED[0] + " && rm -rf backend",                  # authorized + extra
                    "echo x > f"]:
            with self.subTest(cmd=cmd):
                res = run_hook(BASH_GUARD, "implementer", bash_payload(cmd, self.project), self.project)
                self.assertEqual(res.returncode, 2, f"should be blocked: {cmd}")

    def test_without_scope_only_read_only(self):
        res = run_hook(BASH_GUARD, "implementer", bash_payload("git status", self.project), self.project)
        self.assertEqual(res.returncode, 0, res.stderr)
        res = run_hook(BASH_GUARD, "implementer", bash_payload(AUTHORIZED[0], self.project), self.project)
        self.assertEqual(res.returncode, 2)
        self.assertIn("active-scope.json", res.stderr)


class EditScopeImplementer(ProjectDir):
    def test_approved_paths_only(self):
        self.write_scope()
        allowed = ["backend/app/controllers/session_controller.py",
                   "frontend/src/pages/ExpiredPage.tsx",
                   os.path.join(self.project, "frontend/src/pages/sub/Deep.tsx")]
        for path in allowed:
            for tool in ("Edit", "Write"):
                with self.subTest(path=path, tool=tool):
                    res = run_hook(EDIT_SCOPE, "implementer", edit_payload(path, self.project, tool), self.project)
                    self.assertEqual(res.returncode, 0, res.stderr)
        blocked = ["backend/app/core/security.py",
                   "frontend/src/App.tsx",
                   "docs/planning/plans/2026-10-30-demo.md",
                   "docs/planning/active-scope.json",
                   ".claude/settings.json",
                   ".claude/factory.json",
                   "/tmp/outside.txt",
                   os.path.expanduser("~/.claude/hooks/bash_guard.py"),
                   os.path.expanduser("~/.claude/settings.json"),
                   "../escape.txt"]
        for path in blocked:
            with self.subTest(path=path):
                res = run_hook(EDIT_SCOPE, "implementer", edit_payload(path, self.project), self.project)
                self.assertEqual(res.returncode, 2, f"should be blocked: {path}")
                self.assertIn("edit_scope: blocked", res.stderr)

    def test_notebook_edit_uses_notebook_path(self):
        self.write_scope(approved_paths=["notebooks/**"])
        res = run_hook(EDIT_SCOPE, "implementer", edit_payload("notebooks/a.ipynb", self.project, "NotebookEdit"), self.project)
        self.assertEqual(res.returncode, 0, res.stderr)
        res = run_hook(EDIT_SCOPE, "implementer", edit_payload("backend/x.ipynb", self.project, "NotebookEdit"), self.project)
        self.assertEqual(res.returncode, 2)

    def test_missing_scope_blocks_everything(self):
        res = run_hook(EDIT_SCOPE, "implementer", edit_payload("backend/app/main.py", self.project), self.project)
        self.assertEqual(res.returncode, 2)
        self.assertIn("fail closed", res.stderr)

    def test_other_tools_are_ignored(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": self.project}
        res = run_hook(EDIT_SCOPE, "implementer", payload, self.project)
        self.assertEqual(res.returncode, 0)


class EditScopeTester(ProjectDir):
    def test_scope_test_paths(self):
        self.write_scope()
        for path in ["backend/tests/test_session.py", "backend/tests/controllers/test_x.py",
                     "frontend/src/pages/Expired.test.tsx"]:
            with self.subTest(path=path):
                res = run_hook(EDIT_SCOPE, "tester", edit_payload(path, self.project), self.project)
                self.assertEqual(res.returncode, 0, res.stderr)
        for path in ["backend/app/controllers/session_controller.py", "frontend/src/pages/ExpiredPage.tsx",
                     "docs/planning/plans/x.md", ".claude/factory.json", "frontend/src/App.spec.ts"]:
            with self.subTest(path=path):
                res = run_hook(EDIT_SCOPE, "tester", edit_payload(path, self.project), self.project)
                self.assertEqual(res.returncode, 2, f"should be blocked: {path}")

    def test_falls_back_to_factory_json_then_defaults(self):
        self.write_scope(test_paths=[])
        self.write_factory(testPaths=["qa/**"])
        res = run_hook(EDIT_SCOPE, "tester", edit_payload("qa/smoke.py", self.project), self.project)
        self.assertEqual(res.returncode, 0, res.stderr)
        res = run_hook(EDIT_SCOPE, "tester", edit_payload("backend/tests/test_a.py", self.project), self.project)
        self.assertEqual(res.returncode, 2)
        os.remove(os.path.join(self.project, ".claude", "factory.json"))
        for path in ["backend/tests/test_a.py", "src/__tests__/a.test.ts", "lib/thing_test.py", "conftest.py"]:
            with self.subTest(path=path):
                res = run_hook(EDIT_SCOPE, "tester", edit_payload(path, self.project), self.project)
                self.assertEqual(res.returncode, 0, res.stderr)
        res = run_hook(EDIT_SCOPE, "tester", edit_payload("src/app.py", self.project), self.project)
        self.assertEqual(res.returncode, 2)

    def test_missing_scope_blocks_tester_too(self):
        res = run_hook(EDIT_SCOPE, "tester", edit_payload("backend/tests/test_a.py", self.project), self.project)
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
