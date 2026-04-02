"""Repository and dependency management subcommands."""
from __future__ import annotations

import json
import re

from core.utils.common import Logger, PROJECT_ROOT, run_proc, run_capture
from core.utils.command_utils import wrap_command
from ._helpers import load_fetch_deps, FETCH_DEPS_FILE


def _impl_cmd_repo_list(args) -> None:
    # List git submodules and fetch deps
    gm = PROJECT_ROOT / ".gitmodules"
    if gm.exists():
        print("Git submodules (.gitmodules):")
        text = gm.read_text(encoding="utf-8")
        for m in re.finditer(r"\[submodule \"([^\"]+)\"\]", text):
            print(" -", m.group(1))
    if FETCH_DEPS_FILE.exists():
        print("Fetch deps:")
        for d in load_fetch_deps():
            print(f" - {d.get('name')} -> {d.get('url')} @ {d.get('tag')}")


def _impl_cmd_repo_add_submodule(args) -> None:
    url = getattr(args, "url")
    dest = getattr(args, "dest")
    branch = getattr(args, "branch", "main")
    dry = getattr(args, "dry_run", False)
    cmd = ["git", "submodule", "add", "-b", branch, url, dest]
    if dry:
        print("Dry-run:", " ".join(cmd))
        return
    run_proc(cmd, cwd=PROJECT_ROOT)
    Logger.info(f"Added submodule {url} -> {dest}")


def _impl_cmd_repo_add_fetch(args) -> None:
    name = getattr(args, "name")
    url = getattr(args, "url")
    tag = getattr(args, "tag", "main")
    dry = getattr(args, "dry_run", False)
    entry = {"name": name, "url": url, "tag": tag}
    if dry:
        print("Dry-run: would record fetch dep:", entry)
        return
    data = list(load_fetch_deps())
    data.append(entry)
    FETCH_DEPS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    Logger.info(f"Recorded fetch dep: {name} -> {url}@{tag}")
    # Clear cached view after writing
    try:
        load_fetch_deps.cache_clear()
    except Exception:
        pass


def _impl_cmd_repo_sync(args) -> None:
    # Initialize and update git submodules, then fetch fetch-deps
    try:
        run_proc(["git", "submodule", "update", "--init", "--recursive"], cwd=PROJECT_ROOT)
    except SystemExit:
        Logger.warn("Submodule update failed")
    if FETCH_DEPS_FILE.exists():
        for d in load_fetch_deps():
            dest = PROJECT_ROOT / "external" / d.get("name")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # attempt pull
                try:
                    run_proc(["git", "-C", str(dest), "fetch"], cwd=PROJECT_ROOT)
                    run_proc(["git", "-C", str(dest), "checkout", d.get("tag")], cwd=PROJECT_ROOT)
                except SystemExit:
                    Logger.warn(f"Failed to update {d.get('name')}")
            else:
                try:
                    run_proc(["git", "clone", d.get("url"), str(dest)], cwd=PROJECT_ROOT)
                    run_proc(["git", "-C", str(dest), "checkout", d.get("tag")], cwd=PROJECT_ROOT)
                except SystemExit:
                    Logger.warn(f"Failed to clone {d.get('name')}")


def _impl_cmd_repo_versions(args) -> None:
    if not FETCH_DEPS_FILE.exists():
        print("No fetch deps recorded")
        return
    for d in load_fetch_deps():
        name = d.get("name")
        url = d.get("url")
        print(f"Versions for {name} ({url}):")
        try:
            out, rc = run_capture(["git", "ls-remote", "--tags", url], cwd=PROJECT_ROOT)
            if rc == 0 and out:
                tags = [line.split('\t')[1] for line in out.splitlines() if '\trefs/tags/' in line]
                for t in tags[:10]:
                    print(" -", t)
        except Exception:
            print("  (failed to list remote tags)")


# ── Wrapper functions ─────────────────────────────────────────────────────────

def cmd_repo_list(args):
    return wrap_command(_impl_cmd_repo_list, args)


def cmd_repo_add_submodule(args):
    return wrap_command(_impl_cmd_repo_add_submodule, args)


def cmd_repo_add_fetch(args):
    return wrap_command(_impl_cmd_repo_add_fetch, args)


def cmd_repo_sync(args):
    return wrap_command(_impl_cmd_repo_sync, args)


def cmd_repo_versions(args):
    return wrap_command(_impl_cmd_repo_versions, args)
