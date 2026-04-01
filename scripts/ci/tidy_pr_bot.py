#!/usr/bin/env python3
"""Simple automation to run `tool format tidy-fix`, create a branch, commit fixes and optionally open a PR.

This script is intentionally conservative: it runs the existing `tool format tidy-fix --apply`
command to produce fixes. If changes are produced it creates a new branch, commits them
and (optionally) opens a PR using the `gh` CLI (if available and configured).

Usage:
  python3 scripts/ci/tidy_pr_bot.py --branch tidy/auto-fixes-<ts> --create-pr
"""
import argparse
import datetime
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run(cmd, check=True, **kwargs):
    logging.info("Running: %s", " ".join(cmd))
    return subprocess.run(cmd, check=check, **kwargs)


def git_has_changes():
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    return bool(res.stdout.strip())


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--branch", default=None)
    p.add_argument("--create-pr", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    branch = args.branch or f"tidy/auto-fixes-{ts}"

    # Run the tidy-fix (this command is provided by the tool)
    try:
        run([sys.executable, "scripts/tool.py", "format", "tidy-fix", "--apply"])
    except subprocess.CalledProcessError:
        logging.error("`tool format tidy-fix` failed")
        return 1

    if not git_has_changes():
        logging.info("No changes produced by tidy-fix; nothing to do.")
        return 0

    if args.dry_run:
        logging.info("Dry-run: changes exist but not committing")
        return 0

    # create branch and commit
    run(["git", "checkout", "-b", branch])
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "chore(tidy): apply clang-tidy --fix changes (auto)"])
    run(["git", "push", "-u", "origin", branch])

    if args.create_pr:
        # Attempt to create a PR using gh CLI
        if shutil_which("gh"):
            run(["gh", "pr", "create", "--fill", "--title", "chore(tidy): apply clang-tidy fixes", "--body", "Auto-generated clang-tidy fixes (please review)"])
        else:
            logging.warning("`gh` CLI not found; cannot create PR automatically. Branch pushed: %s", branch)

    logging.info("Tidy fixes pushed to branch: %s", branch)
    return 0


def shutil_which(name):
    from shutil import which

    return which(name) is not None


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Run clang-tidy fixes, commit to a branch and open a PR (if possible).

This script expects a working git repo and optionally GITHUB_TOKEN in env for API PR creation.
If `gh` CLI is available it will be used; otherwise the script will push the branch and print instructions.
"""
import argparse
import datetime
import os
import subprocess
import sys
import shutil


def run(cmd, check=True, **kwargs):
    print("$", " ".join(cmd))
    return subprocess.run(cmd, check=check, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", help="branch name to create (auto-generated if omitted)")
    parser.add_argument("--push", action="store_true", help="push branch to origin")
    parser.add_argument("--create-pr", action="store_true", help="attempt to create a PR")
    args = parser.parse_args()

    ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    branch = args.branch or f"auto/tidy-fixes-{ts}"

    # Run the tidy-fix tool (assumes it is available via scripts/tool.py)
    try:
        run([sys.executable, "scripts/tool.py", "format", "tidy-fix", "--apply"])
    except subprocess.CalledProcessError:
        print("tidy-fix tool failed or made no changes; continuing if there are local changes")

    # Check for changes
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("No changes to commit after tidy-fix. Exiting.")
        return 0

    # Create branch
    run(["git", "checkout", "-b", branch])
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "chore(tidy): apply clang-tidy --fix automated changes"])

    if args.push:
        run(["git", "push", "-u", "origin", branch])

    if args.create_pr:
        # Prefer gh CLI if available
        if shutil.which("gh"):
            run(["gh", "pr", "create", "--title", "chore(tidy): apply clang-tidy fixes", "--body", "Automated tidy fixes.", "--base", "main"])
        else:
            token = os.environ.get("GITHUB_TOKEN")
            if token:
                print("GITHUB_TOKEN present but gh CLI not found; PR creation via API is not implemented in this script.")
            else:
                print("No GH credentials available; pushed branch but cannot create PR automatically.")

    print("Done. Branch:", branch)
    return 0


if __name__ == "__main__":
    import shutil
    sys.exit(main())
