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
