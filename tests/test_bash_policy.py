"""Tests for hooks/bash_policy.py (global Bash policy that sees through the RTK wrapper).

    python3 -m unittest -v tests/test_bash_policy.py
"""

import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks", "bash_policy.py")


def run(command: str) -> subprocess.CompletedProcess:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": "/tmp", "tool_input": {"command": command}}
    return subprocess.run([sys.executable, "-I", HOOK], input=json.dumps(payload), capture_output=True, text=True)


def decision(res: subprocess.CompletedProcess) -> str:
    if res.returncode == 2:
        return "deny"
    if res.stdout.strip():
        return json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"]
    return "none"


class SecretFiles(unittest.TestCase):
    DENY = [
        "cat .env", "rtk read .env", "rtk cat .env", "rtk proxy cat .env", "head -3 .env.local",
        "cat backend/.env.production", "sed -n 1,5p ./.env", "cat ~/.ssh/id_rsa", "cat ~/.aws/credentials",
        "cat deploy/server.pem", "cat keys/app.p12", "cat ~/.config/gcloud/application_default_credentials.json",
        "cat backend/vertex-service-account.json", "cat creds/google_credentials.json", "ls secrets/",
        "cat ~/.npmrc", "cat ~/.netrc", "grep TOKEN .env", "python3 -c 'print(1)' && cat .env",
        "cat src/app.py | tee .env", "cat '.env'", 'cat ".env.staging"', "cat ~/.docker/config.json",
    ]
    ALLOW = [
        "cat .env.example", "rtk read .env.example", "cat .env.sample", "cat config/.env.template",
        "cat src/app.py", "git status", "ls -la", "grep -rn SECRET src/", "cat environment.md",
        "cat .envrc.example", "python3 -m pytest tests -q", "cat README.md",
    ]

    def test_denied(self):
        for cmd in self.DENY:
            with self.subTest(cmd=cmd):
                res = run(cmd)
                self.assertEqual(decision(res), "deny", f"{cmd!r}: {res.stdout} {res.stderr}")
                self.assertIn("bash_policy: blocked", res.stderr)

    def test_allowed(self):
        for cmd in self.ALLOW:
            with self.subTest(cmd=cmd):
                self.assertEqual(decision(run(cmd)), "none", cmd)


class ConsequentialCommands(unittest.TestCase):
    ASK = [
        "git commit -m x", "rtk git commit -m x", "git push", "rtk git push origin main", "git push --force",
        "git merge develop", "git rebase main", "git reset --hard HEAD~1", "git tag v1",
        "alembic upgrade head", ".venv/bin/alembic upgrade head", "cd backend && .venv/bin/alembic downgrade -1",
        "alembic stamp head", "docker push repo/img:1", "docker compose up -d", "docker-compose up",
        "kubectl apply -f k8s/", "kubectl delete pod x", "terraform apply", "terraform destroy",
        "ssh user@host", "scp a user@host:b", "rsync -av a/ host:b/", "gcloud run deploy svc --image x",
        "gh pr create --fill", "gh pr merge 12", "gh release create v1", "ls && git push",
    ]
    NONE = [
        "git status", "git diff", "git log --oneline", "rtk git status", "git commit --help | head -1" if False else "git show HEAD",
        "alembic heads", ".venv/bin/alembic current", "docker ps", "docker compose ps", "kubectl get pods",
        "terraform plan", "gh pr view 12", "gh pr list", "echo git push", "cat notes/git-push-guide.md",
    ]

    def test_ask(self):
        for cmd in self.ASK:
            with self.subTest(cmd=cmd):
                res = run(cmd)
                self.assertEqual(decision(res), "ask", f"{cmd!r}: {res.stdout} {res.stderr}")

    def test_no_opinion(self):
        for cmd in self.NONE:
            with self.subTest(cmd=cmd):
                self.assertEqual(decision(run(cmd)), "none", cmd)


class Robustness(unittest.TestCase):
    def test_non_bash_and_bad_input_pass_through(self):
        payload = {"tool_name": "Read", "tool_input": {"file_path": ".env"}}
        res = subprocess.run([sys.executable, "-I", HOOK], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        res = subprocess.run([sys.executable, "-I", HOOK], input="garbage", capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_unbalanced_quotes_still_checked(self):
        self.assertEqual(decision(run("cat .env 'oops")), "deny")


if __name__ == "__main__":
    unittest.main()
