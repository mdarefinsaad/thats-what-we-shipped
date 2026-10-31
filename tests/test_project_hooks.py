"""Tests for the generic per-project hooks (project/hooks/).

    python3 -m unittest -v tests/test_project_hooks.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "project", "hooks")
LINT = os.path.join(HOOKS, "lint_changed_file.py")
FORBID = os.path.join(HOOKS, "forbidden_patterns.py")


def run_hook(script: str, payload: dict, project: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project)
    return subprocess.run([sys.executable, "-I", script], input=json.dumps(payload), capture_output=True, text=True, env=env)


class ProjectDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = os.path.realpath(self.tmp.name)
        os.makedirs(os.path.join(self.project, ".claude"))
        os.makedirs(os.path.join(self.project, "src"))
        os.makedirs(os.path.join(self.project, "backend", "app"))

    def tearDown(self):
        self.tmp.cleanup()

    def write_factory(self, **cfg):
        with open(os.path.join(self.project, ".claude", "factory.json"), "w") as fh:
            json.dump(cfg, fh)

    def touch(self, rel: str, content: str = "x\n") -> str:
        path = os.path.join(self.project, rel)
        with open(path, "w") as fh:
            fh.write(content)
        return path


class LintChangedFile(ProjectDir):
    def payload(self, rel: str) -> dict:
        return {"tool_name": "Edit", "cwd": self.project, "tool_input": {"file_path": os.path.join(self.project, rel)}}

    def test_runs_matching_command_and_reports_failure(self):
        self.write_factory(lintOnEdit=[{"glob": "src/**/*.py", "command": "grep -q TODO {file} && echo 'TODO found' && exit 1 || exit 0"}])
        clean = self.touch("src/a.py", "ok\n")
        self.assertEqual(run_hook(LINT, self.payload("src/a.py"), self.project).returncode, 0)
        self.touch("src/a.py", "TODO\n")
        res = run_hook(LINT, self.payload("src/a.py"), self.project)
        self.assertEqual(res.returncode, 2)
        self.assertIn("TODO found", res.stderr)
        self.assertIn("Lint problems in src/a.py", res.stderr)

    def test_non_matching_file_and_missing_config_are_silent(self):
        self.touch("src/a.ts")
        self.assertEqual(run_hook(LINT, self.payload("src/a.ts"), self.project).returncode, 0)
        self.write_factory(lintOnEdit=[{"glob": "src/**/*.py", "command": "exit 1"}])
        self.assertEqual(run_hook(LINT, self.payload("src/a.ts"), self.project).returncode, 0)
        self.assertEqual(run_hook(LINT, self.payload("src/missing.py"), self.project).returncode, 0)

    def test_cwd_venv_and_brace_glob(self):
        os.makedirs(os.path.join(self.project, "backend", ".venv", "bin"))
        self.touch("backend/.venv/bin/tool", "#!/bin/sh\necho ran-in-$(basename $(pwd)) >&2\nexit 1\n")
        os.chmod(os.path.join(self.project, "backend", ".venv", "bin", "tool"), 0o755)
        self.write_factory(lintOnEdit=[{"glob": "backend/**/*.{py,pyi}", "cwd": "backend", "venv": ".venv/bin", "command": "{venv}/tool {file}"}])
        self.touch("backend/app/x.pyi")
        res = run_hook(LINT, self.payload("backend/app/x.pyi"), self.project)
        self.assertEqual(res.returncode, 2)
        self.assertIn("ran-in-backend", res.stderr)


class ForbiddenPatterns(ProjectDir):
    RULES = [
        {"glob": "backend/app/**/*.py", "pattern": r"^\s*print\(", "flags": "m", "message": "no print()"},
        {"glob": "backend/app/**/*.py", "pattern": r"SELECT\s+\*", "flags": "i", "message": "no SELECT *"},
    ]

    def edit(self, rel: str, old: str, new: str, tool: str = "Edit") -> dict:
        inp = {"file_path": os.path.join(self.project, rel)}
        if tool == "Write":
            inp["content"] = new
        else:
            inp.update(old_string=old, new_string=new)
        return {"tool_name": tool, "cwd": self.project, "tool_input": inp}

    def test_blocks_new_violation_only(self):
        self.write_factory(forbiddenPatterns=self.RULES)
        res = run_hook(FORBID, self.edit("backend/app/a.py", "x = 1", "x = 1\nprint(x)"), self.project)
        self.assertEqual(res.returncode, 2)
        self.assertIn("no print()", res.stderr)
        # moving an existing print() around is not a new violation
        res = run_hook(FORBID, self.edit("backend/app/a.py", "print(x)\ny = 2", "y = 2\nprint(x)"), self.project)
        self.assertEqual(res.returncode, 0, res.stderr)
        # removing one is fine
        res = run_hook(FORBID, self.edit("backend/app/a.py", "print(x)", ""), self.project)
        self.assertEqual(res.returncode, 0)

    def test_write_tool_case_insensitive_and_glob_scope(self):
        self.write_factory(forbiddenPatterns=self.RULES)
        res = run_hook(FORBID, self.edit("backend/app/repo.py", "", 'q = "select * from t"', tool="Write"), self.project)
        self.assertEqual(res.returncode, 2)
        self.assertIn("no SELECT *", res.stderr)
        # same content outside the glob passes
        res = run_hook(FORBID, self.edit("src/notes.py", "", 'q = "select * from t"', tool="Write"), self.project)
        self.assertEqual(res.returncode, 0)

    def test_missing_config_or_other_tool_passes(self):
        res = run_hook(FORBID, self.edit("backend/app/a.py", "", "print(1)", tool="Write"), self.project)
        self.assertEqual(res.returncode, 0)
        self.write_factory(forbiddenPatterns=self.RULES)
        payload = {"tool_name": "Bash", "cwd": self.project, "tool_input": {"command": "print(1)"}}
        self.assertEqual(run_hook(FORBID, payload, self.project).returncode, 0)


if __name__ == "__main__":
    unittest.main()
