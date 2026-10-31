#!/usr/bin/env python3
"""Install "That's What We Shipped" into ~/.claude, or remove it again.

    python3 install.py              install / update
    python3 install.py --dry-run    show what would change, touch nothing
    python3 install.py --check      report drift between repo and ~/.claude
    python3 install.py --uninstall  remove installed files, restore backups

    python3 install.py --project <repo> [--force]
        copy the optional per-project kit (project/skills, project/hooks,
        project/rules) into <repo>/.claude/. Existing files are kept unless
        --force. Nothing global changes.

Owned files are recorded in ~/.claude/.factory-manifest.json so uninstall
removes exactly what install created. settings.json and CLAUDE.md are backed
up once (first install) as *.pre-factory and restored on uninstall.
"""

import copy
import filecmp
import json
import os
import shutil
import stat
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
CLAUDE_HOME = os.path.expanduser("~/.claude")
MANIFEST = os.path.join(CLAUDE_HOME, ".factory-manifest.json")
SETTINGS = os.path.join(CLAUDE_HOME, "settings.json")
SETTINGS_BACKUP = SETTINGS + ".pre-factory"
CLAUDE_MD = os.path.join(CLAUDE_HOME, "CLAUDE.md")
CLAUDE_MD_BACKUP = CLAUDE_MD + ".pre-factory"
FRAGMENT = os.path.join(REPO, "settings.fragment.json")

COPY_DIRS = ("agents", "skills", "hooks")


def planned_copies() -> list[tuple[str, str]]:
    """(source, destination) for every file the install owns."""
    pairs = []
    for sub in COPY_DIRS:
        root = os.path.join(REPO, sub)
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if name.startswith(".") or name.endswith(".pyc"):
                    continue
                src = os.path.join(dirpath, name)
                rel = os.path.relpath(src, REPO)
                pairs.append((src, os.path.join(CLAUDE_HOME, rel)))
    pairs.append((os.path.join(REPO, "CLAUDE.md"), CLAUDE_MD))
    return pairs


def read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def merge_settings(existing: dict, fragment: dict) -> dict:
    """Return a new settings dict: `existing` with `fragment` merged in.

    Must hold:
      - nothing the user already has is lost (their hooks, plugins, env, voice...)
      - fragment lists (permissions.deny / .ask, hook arrays) are added to the
        user's lists without creating duplicates, and running install twice
        gives the same result as running it once
      - fragment dicts merge recursively (hooks.Stop is added next to the
        user's existing hooks.PreToolUse; enabledPlugins gains one key)
      - a fragment scalar (model: "opus") replaces the user's value
    Neither input is mutated.
    """
    result = copy.deepcopy(existing)
    for key, value in fragment.items():
        current = result.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            result[key] = merge_settings(current, value)
        elif isinstance(value, list) and isinstance(current, list):
            merged = list(current)
            for item in value:
                if item not in merged:  # equality, so identical hook dicts count as duplicates
                    merged.append(item)
            result[key] = merged
        else:
            result[key] = copy.deepcopy(value)
    return result


def install(dry_run: bool) -> None:
    pairs = planned_copies()
    print(f"{'Would copy' if dry_run else 'Copying'} {len(pairs)} files into {CLAUDE_HOME}")
    for src, dst in pairs:
        state = "new" if not os.path.exists(dst) else ("same" if filecmp.cmp(src, dst, shallow=False) else "update")
        print(f"  [{state:6}] {os.path.relpath(dst, CLAUDE_HOME)}")
        if dry_run:
            continue
        if dst == CLAUDE_MD and os.path.exists(CLAUDE_MD) and not os.path.exists(CLAUDE_MD_BACKUP):
            shutil.copy2(CLAUDE_MD, CLAUDE_MD_BACKUP)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        if dst.startswith(os.path.join(CLAUDE_HOME, "hooks")):
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR)

    existing = read_json(SETTINGS)
    fragment = read_json(FRAGMENT)
    merged = merge_settings(existing, fragment)
    changed = merged != existing
    print(f"settings.json: {'would change' if changed else 'unchanged'}"
          f" (model → {merged.get('model')!r}, deny rules: {len(merged.get('permissions', {}).get('deny', []))},"
          f" ask rules: {len(merged.get('permissions', {}).get('ask', []))})")
    if not dry_run:
        if os.path.exists(SETTINGS) and not os.path.exists(SETTINGS_BACKUP):
            shutil.copy2(SETTINGS, SETTINGS_BACKUP)
            print(f"  backed up settings.json → {os.path.basename(SETTINGS_BACKUP)}")
        if changed:
            write_json(SETTINGS, merged)
        write_json(MANIFEST, {
            "repo": REPO,
            "files": sorted(dst for _src, dst in pairs),
            "settings_backup": SETTINGS_BACKUP if os.path.exists(SETTINGS_BACKUP) else None,
            "claude_md_backup": CLAUDE_MD_BACKUP if os.path.exists(CLAUDE_MD_BACKUP) else None,
        })
        print(f"manifest written: {MANIFEST}")
    print("Done." if not dry_run else "Dry run only; nothing changed.")


def check() -> int:
    drift = 0
    for src, dst in planned_copies():
        if not os.path.exists(dst):
            print(f"  missing : {os.path.relpath(dst, CLAUDE_HOME)}")
            drift += 1
        elif not filecmp.cmp(src, dst, shallow=False):
            print(f"  differs : {os.path.relpath(dst, CLAUDE_HOME)}")
            drift += 1
    merged = merge_settings(read_json(SETTINGS), read_json(FRAGMENT))
    if merged != read_json(SETTINGS):
        print("  settings.json lacks part of settings.fragment.json")
        drift += 1
    print("No drift." if drift == 0 else f"{drift} item(s) drifted; run install.py to resync.")
    return 0 if drift == 0 else 1


def uninstall() -> None:
    manifest = read_json(MANIFEST)
    if not manifest:
        print("No manifest found; nothing to uninstall.")
        return
    for path in manifest.get("files", []):
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed {os.path.relpath(path, CLAUDE_HOME)}")
    for sub in COPY_DIRS:
        for dirpath, dirs, files in os.walk(os.path.join(CLAUDE_HOME, sub), topdown=False):
            if not dirs and not files:
                os.rmdir(dirpath)
    for backup, target in ((manifest.get("settings_backup"), SETTINGS), (manifest.get("claude_md_backup"), CLAUDE_MD)):
        if backup and os.path.exists(backup):
            shutil.move(backup, target)
            print(f"  restored {os.path.basename(target)} from backup")
    os.remove(MANIFEST)
    print("Uninstalled.")


PROJECT_KIT = (("project/skills", "skills"), ("project/hooks", "hooks"), ("project/rules", "rules"))


def install_project(project: str, force: bool) -> None:
    project = os.path.abspath(os.path.expanduser(project))
    if not os.path.isdir(project):
        print(f"not a directory: {project}")
        sys.exit(2)
    target_root = os.path.join(project, ".claude")
    copied = kept = 0
    for src_name, dst_name in PROJECT_KIT:
        src_root = os.path.join(REPO, src_name)
        for dirpath, _dirs, files in os.walk(src_root):
            for name in files:
                if name.startswith(".") or name.endswith(".pyc"):
                    continue
                src = os.path.join(dirpath, name)
                rel = os.path.relpath(src, src_root)
                dst = os.path.join(target_root, dst_name, rel)
                if os.path.exists(dst) and not force:
                    state = "same" if filecmp.cmp(src, dst, shallow=False) else "kept (differs; --force to overwrite)"
                    kept += 1
                else:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    if dst_name == "hooks":
                        os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR)
                    state = "copied"
                    copied += 1
                print(f"  [{state}] .claude/{dst_name}/{rel}")
    print(f"Project kit → {target_root}: {copied} copied, {kept} already present.")


def main() -> None:
    argv = sys.argv[1:]
    if argv[:1] == ["--project"] and len(argv) in (2, 3) and (len(argv) == 2 or argv[2] == "--force"):
        install_project(argv[1], force=len(argv) == 3)
        return
    args = set(argv)
    if args - {"--dry-run", "--check", "--uninstall"} or len(args) > 1:
        print(__doc__)
        sys.exit(2)
    if "--uninstall" in args:
        uninstall()
    elif "--check" in args:
        sys.exit(check())
    else:
        install(dry_run="--dry-run" in args)


if __name__ == "__main__":
    main()
