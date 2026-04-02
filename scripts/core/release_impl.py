#!/usr/bin/env python3
"""Release helper for the repository.

Provides a simple CLI to bump/set the repository version and synchronize
the common version holders across the repository (CMakeLists, pyproject,
extension package.json, etc.). The canonical source of truth is the
`VERSION` file at the repository root; this script updates that file and
then applies sane replacements to other files.

Usage examples:
  python3 scripts/release.py bump minor --dry-run
  python3 scripts/release.py set 1.2.0+0
  python3 scripts/release.py set-revision 42
  python3 scripts/release.py tag --push

This script uses `Transaction` to apply changes atomically and will
commit the changes (and optionally tag) using `git`.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import sys
from pathlib import Path as _Path

# Ensure `scripts/` is on sys.path so we can import `core.*` packages.
SCRIPTS_DIR = _Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from core.utils.fileops import Transaction
from core.utils.version import read_version_file, write_version_file, Version, guess_revision_from_git
from core.utils.common import PROJECT_ROOT, Logger


VERSION_PATH = PROJECT_ROOT / "VERSION"


def update_files(v: Version, dry_run: bool = False) -> None:
    base = v.base()

    changes = []

    # 1) Update top-level CMakeLists.txt (project VERSION)
    cmake = PROJECT_ROOT / "CMakeLists.txt"
    if cmake.exists():
        txt = cmake.read_text(encoding="utf-8")
        new_txt, n = re.subn(r'(project\([^\n]*VERSION\s+)([0-9.]+)', lambda m: m.group(1) + base, txt, flags=re.IGNORECASE)
        if n:
            changes.append((cmake, new_txt))

    # 2) Update pyproject.toml version = "..."
    pyproj = PROJECT_ROOT / "pyproject.toml"
    if pyproj.exists():
        txt = pyproj.read_text(encoding="utf-8")
        new_txt, n = re.subn(r'(version\s*=\s*")([^"]+)(")', lambda m: m.group(1) + base + m.group(3), txt)
        if n:
            changes.append((pyproj, new_txt))

    # 3) Update extension/package.json
    ext_pkg = PROJECT_ROOT / "extension" / "package.json"
    if ext_pkg.exists():
        data = json.loads(ext_pkg.read_text(encoding="utf-8"))
        if data.get("version") != base:
            data["version"] = base
            changes.append((ext_pkg, json.dumps(data, indent=2) + "\n"))

    # 4) Update extension/package-lock.json (best-effort)
    ext_lock = PROJECT_ROOT / "extension" / "package-lock.json"
    if ext_lock.exists():
        try:
            data = json.loads(ext_lock.read_text(encoding="utf-8"))
            if data.get("version") != base:
                data["version"] = base
                changes.append((ext_lock, json.dumps(data, indent=2) + "\n"))
        except Exception:
            Logger.warn("Failed to parse extension/package-lock.json; skipping")

    # 5) Update extension UI default version strings (best-effort regex)
    ext_js = PROJECT_ROOT / "extension" / "src" / "extension.js"
    if ext_js.exists():
        txt = ext_js.read_text(encoding="utf-8")
        # replace value: '1.0.5' or value: '1.0.0' occurrences in showInputBox default
        new_txt, n = re.subn(r"(value:\s*')([0-9.]+(?:\.[0-9.]+)*(?:\+\d+)?)(')", lambda m: m.group(1) + str(v) + m.group(3), txt)
        if n:
            changes.append((ext_js, new_txt))

    # Filter out files that are git-ignored (e.g. package-lock.json). We can't `git add` ignored files.
    if changes:
        filtered: list[tuple[_Path, str]] = []
        for p, txt in changes:
            try:
                # git check-ignore returns 0 if the path is ignored
                res = subprocess.run(["git", "check-ignore", "-q", str(p)], cwd=PROJECT_ROOT)
                if res.returncode == 0:
                    Logger.warn(f"Skipping {p} because it's git-ignored")
                else:
                    filtered.append((p, txt))
            except Exception:
                # If git is not available or check fails, keep the file to avoid silent drops
                filtered.append((p, txt))
        changes = filtered

    if not changes:
        Logger.info("No file updates necessary (other files already in sync).")
        return

    if dry_run:
        Logger.info("Dry-run: the following changes would be applied:")
        for p, txt in changes:
            print(f"- {p}")
        return

    # Apply changes transactionally
    with Transaction(PROJECT_ROOT) as txn:
        # write VERSION first
        write_version_file(VERSION_PATH, v)

        for p, txt in changes:
            txn.safe_write_text(p, txt)

        # commit changes
        try:
            subprocess.run(["git", "add", str(VERSION_PATH)], check=True, cwd=PROJECT_ROOT)
            for p, _ in changes:
                subprocess.run(["git", "add", str(p)], check=True, cwd=PROJECT_ROOT)
            subprocess.run(["git", "commit", "-m", f"Bump version to {v}"], check=True, cwd=PROJECT_ROOT)
        except subprocess.CalledProcessError as e:
            Logger.error(f"Git commit failed: {e}")
            raise


# ---------------------------------------------------------------------------
# Publish / unpublish helpers
# ---------------------------------------------------------------------------

def _get_project_name() -> str:
    """Extract project name from top-level CMakeLists.txt."""
    cmake = PROJECT_ROOT / "CMakeLists.txt"
    if cmake.exists():
        m = re.search(r'project\(\s*(\w+)', cmake.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return PROJECT_ROOT.name


def _require_tool(name: str) -> str:
    """Return the full path of *name* or raise a clear error."""
    found = shutil.which(name)
    if not found:
        raise RuntimeError(
            f"Required tool '{name}' not found in PATH.\n"
            f"Install it and make sure it is on PATH before running this command."
        )
    return found


def _find_cpack_artifacts(build_dir: Path) -> list[Path]:
    """Return CPack-generated packages located in *build_dir*."""
    artifacts: list[Path] = []
    for pat in ("*.tar.gz", "*.tar.xz", "*.zip", "*.deb", "*.rpm", "*.pkg.tar.zst"):
        artifacts.extend(build_dir.glob(pat))
    return sorted(artifacts)


# --- GitHub ------------------------------------------------------------------

def publish_github(
    v: Version,
    dry_run: bool,
    signing_key: str | None,
    notes: str | None,
    build_dir: Path,
) -> None:
    tag = f"v{v.base()}"
    gh = _require_tool("gh")

    artifacts = _find_cpack_artifacts(build_dir)
    if artifacts:
        Logger.info(f"Found {len(artifacts)} CPack artifact(s):")
        for a in artifacts:
            Logger.info(f"  {a.name}")
    else:
        Logger.warn(
            "No CPack artifacts found in build/.\n"
            "Run: cmake --build --preset <preset> --target package\n"
            "Continuing — release will be created as a draft without binaries."
        )

    cmd = [
        gh, "release", "create", tag,
        "--title", tag,
        "--notes", notes or f"Release {tag}",
    ]
    if not artifacts:
        cmd.append("--draft")
    else:
        cmd.extend(str(a) for a in artifacts)

    Logger.info(f"GitHub: gh release create {tag} ...")
    if dry_run:
        Logger.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        return
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    Logger.success(f"GitHub release {tag} created.")


def unpublish_github(v: Version, dry_run: bool, keep_tag: bool) -> None:
    tag = f"v{v.base()}"
    gh = _require_tool("gh")

    cmd = [gh, "release", "delete", tag, "--yes"]
    if not keep_tag:
        cmd.append("--cleanup-tag")

    Logger.info(f"GitHub: deleting release {tag} ...")
    if dry_run:
        Logger.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        return
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    Logger.success(f"GitHub release {tag} deleted{'' if keep_tag else ' (tag removed)'}.")


# --- Conan -------------------------------------------------------------------

def _conan_ref(v: Version, user: str, channel: str) -> str:
    name = _get_project_name().lower().replace("-", "_")
    if user and channel:
        return f"{name}/{v.base()}@{user}/{channel}"
    return f"{name}/{v.base()}"


def publish_conan(
    v: Version,
    dry_run: bool,
    remote: str,
    user: str,
    channel: str,
) -> None:
    ref = _conan_ref(v, user, channel)
    conan = _require_tool("conan")

    cmd = [conan, "upload", ref, "--remote", remote, "--confirm"]
    Logger.info(f"Conan: uploading {ref} → {remote} ...")
    if dry_run:
        Logger.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        return
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    Logger.success(f"Conan package {ref} uploaded to '{remote}'.")


def unpublish_conan(
    v: Version,
    dry_run: bool,
    remote: str,
    user: str,
    channel: str,
) -> None:
    ref = _conan_ref(v, user, channel)
    conan = _require_tool("conan")

    cmd = [conan, "remove", ref, "--remote", remote, "--confirm"]
    Logger.info(f"Conan: removing {ref} from '{remote}' ...")
    if dry_run:
        Logger.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        return
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)
    Logger.success(f"Conan package {ref} removed from '{remote}'.")


# --- vcpkg overlay port ------------------------------------------------------

def publish_vcpkg(v: Version, dry_run: bool) -> None:
    project = _get_project_name()
    name_lower = project.lower()
    port_dir = PROJECT_ROOT / "ports" / name_lower

    portfile_content = f"""\
# Auto-generated vcpkg overlay port for {project} {v.base()}
# Fill in the SHA512 after the first download, then remove this comment.
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO "<owner>/{project}"
    REF "v{v.base()}"
    SHA512 0  # TODO: replace with actual SHA512
    HEAD_REF main
)

vcpkg_cmake_configure(
    SOURCE_PATH "${{SOURCE_PATH}}"
)
vcpkg_cmake_install()
vcpkg_cmake_config_fixup()

file(REMOVE_RECURSE "${{CURRENT_PACKAGES_DIR}}/debug/include")
vcpkg_install_copyright(FILE_LIST "${{SOURCE_PATH}}/LICENSE")
"""

    vcpkg_manifest = {
        "name": name_lower,
        "version": v.base(),
        "description": f"{project} — generated vcpkg overlay port",
        "dependencies": [],
    }

    Logger.info(f"vcpkg: scaffolding overlay port at {port_dir}/")
    if dry_run:
        Logger.info(f"[DRY-RUN] Would create {port_dir}/portfile.cmake")
        Logger.info(f"[DRY-RUN] Would create {port_dir}/vcpkg.json")
        return

    port_dir.mkdir(parents=True, exist_ok=True)
    (port_dir / "portfile.cmake").write_text(portfile_content, encoding="utf-8")
    (port_dir / "vcpkg.json").write_text(
        json.dumps(vcpkg_manifest, indent=2) + "\n", encoding="utf-8"
    )
    Logger.success(f"vcpkg overlay port scaffolded at {port_dir}/")
    Logger.info("Next steps: fill in the SHA512 in portfile.cmake, then submit to a vcpkg registry.")


def unpublish_vcpkg(v: Version, dry_run: bool) -> None:
    name_lower = _get_project_name().lower()
    port_dir = PROJECT_ROOT / "ports" / name_lower

    if not port_dir.exists():
        Logger.warn(f"vcpkg port directory not found: {port_dir} — nothing to remove.")
        return

    Logger.info(f"vcpkg: removing overlay port at {port_dir}/")
    if dry_run:
        Logger.info(f"[DRY-RUN] Would remove: {port_dir}/")
        return
    shutil.rmtree(port_dir)
    Logger.success(f"vcpkg overlay port removed: {port_dir}/")


# ---------------------------------------------------------------------------

def create_tag(v: Version, push: bool = False, signing_key: str | None = None) -> None:
    tag_name = f"v{v.base()}"  # tag only with base version, omit +revision
    try:
        tag_cmd = ["git", "tag"]
        if signing_key:
            tag_cmd.extend(["-s", "-u", signing_key])
        else:
            tag_cmd.append("-a")
        tag_cmd.extend([tag_name, "-m", f"Release {v}"])
        subprocess.run(tag_cmd, check=True, cwd=PROJECT_ROOT)
        Logger.success(f"Created tag {tag_name}")
        if push:
            subprocess.run(["git", "push", "origin", tag_name], check=True, cwd=PROJECT_ROOT)
            Logger.success(f"Pushed tag {tag_name} to origin")
    except subprocess.CalledProcessError as e:
        Logger.error(f"Git tag/push failed: {e}")
        raise


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="scripts/release.py")
    p.add_argument("--install", action="store_true", help="Install dev dependencies into .venv before running")
    p.add_argument("--recreate", action="store_true", help="Recreate the venv when used with --install")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("bump", help="Bump a part of the version")
    pb.add_argument("part", choices=["major", "middle", "minor"], help="Which part to bump")
    pb.add_argument("--dry-run", action="store_true")

    ps = sub.add_parser("set", help="Set exact version string (e.g. 1.2.3+45)")
    ps.add_argument("version")
    ps.add_argument("--dry-run", action="store_true")

    pr = sub.add_parser("set-revision", help="Set only the revision/build metadata")
    pr.add_argument("revision", type=int)
    pr.add_argument("--dry-run", action="store_true")

    pt = sub.add_parser("tag", help="Create git tag for current base version")
    pt.add_argument("--push", action="store_true", help="Push tag to origin")
    pt.add_argument("--dry-run", action="store_true")
    pt.add_argument("--signing-key", default=None, metavar="KEY_ID",
                    help="GPG key ID for signing the tag (uses git tag -s)")

    pp = sub.add_parser("publish", help="Publish release artifacts to a target registry")
    pp.add_argument(
        "--to", dest="target", required=True,
        choices=["github", "conan", "vcpkg"],
        help="Publish target: github | conan | vcpkg",
    )
    pp.add_argument("--dry-run", action="store_true")
    pp.add_argument("--signing-key", default=None, metavar="KEY_ID",
                    help="GPG key ID for signing artifacts (GitHub only, future use)")
    pp.add_argument("--notes", default=None, metavar="TEXT",
                    help="Release notes text (GitHub only)")
    pp.add_argument("--build-dir", default=None, metavar="DIR",
                    help="Directory to search for CPack artifacts (default: build/)")
    pp.add_argument("--remote", default="conancenter", metavar="REMOTE",
                    help="Conan remote name (default: conancenter)")
    pp.add_argument("--conan-user", default="", metavar="USER",
                    help="Conan package user (leave empty for no user/channel)")
    pp.add_argument("--conan-channel", default="", metavar="CHANNEL",
                    help="Conan package channel (leave empty for no user/channel)")

    pu = sub.add_parser("unpublish", help="Delete/retract a previously published release")
    pu.add_argument(
        "--to", dest="target", required=True,
        choices=["github", "conan", "vcpkg"],
        help="Target to delete from: github | conan | vcpkg",
    )
    pu.add_argument("--dry-run", action="store_true")
    pu.add_argument("--keep-tag", action="store_true",
                    help="GitHub: keep the git tag when deleting the release")
    pu.add_argument("--remote", default="conancenter", metavar="REMOTE",
                    help="Conan remote name (default: conancenter)")
    pu.add_argument("--conan-user", default="", metavar="USER")
    pu.add_argument("--conan-channel", default="", metavar="CHANNEL")

    args = p.parse_args(argv)

    # Optional per-script install helper
    if getattr(args, "install", False):
        try:
            from core.utils.common import install_dev_env
            install_dev_env(recreate=bool(getattr(args, "recreate", False)))
        except Exception as e:
            Logger.warn(f"Dev install helper failed: {e}")

    current = read_version_file(VERSION_PATH)

    if args.cmd == "bump":
        if args.part == "major":
            new = current.bump_major()
        elif args.part == "middle":
            new = current.bump_middle()
        else:
            new = current.bump_minor()
        # default revision: keep existing if non-null, otherwise guess from git
        if new.revision is None:
            new = new.set_revision(guess_revision_from_git())
        update_files(new, dry_run=bool(args.dry_run))
        return 0

    if args.cmd == "set":
        new = Version.parse(args.version)
        update_files(new, dry_run=bool(args.dry_run))
        return 0

    if args.cmd == "set-revision":
        new = current.set_revision(args.revision)
        update_files(new, dry_run=bool(args.dry_run))
        return 0

    if args.cmd == "tag":
        signing_key = getattr(args, "signing_key", None)
        dry = bool(getattr(args, "dry_run", False))
        if dry:
            tag_name = f"v{current.base()}"
            Logger.info(f"[DRY-RUN] Would create tag {tag_name}")
            if args.push:
                Logger.info(f"[DRY-RUN] Would push tag {tag_name} to origin")
        else:
            create_tag(current, push=bool(args.push), signing_key=signing_key)
        return 0

    if args.cmd == "publish":
        dry = bool(args.dry_run)
        target = args.target
        try:
            if target == "github":
                bd = Path(args.build_dir) if args.build_dir else PROJECT_ROOT / "build"
                publish_github(
                    current, dry_run=dry,
                    signing_key=args.signing_key,
                    notes=args.notes,
                    build_dir=bd,
                )
            elif target == "conan":
                publish_conan(
                    current, dry_run=dry,
                    remote=args.remote,
                    user=args.conan_user,
                    channel=args.conan_channel,
                )
            elif target == "vcpkg":
                publish_vcpkg(current, dry_run=dry)
        except RuntimeError as e:
            Logger.error(str(e))
            return 1
        return 0

    if args.cmd == "unpublish":
        dry = bool(args.dry_run)
        target = args.target
        try:
            if target == "github":
                unpublish_github(current, dry_run=dry, keep_tag=bool(args.keep_tag))
            elif target == "conan":
                unpublish_conan(
                    current, dry_run=dry,
                    remote=args.remote,
                    user=args.conan_user,
                    channel=args.conan_channel,
                )
            elif target == "vcpkg":
                unpublish_vcpkg(current, dry_run=dry)
        except RuntimeError as e:
            Logger.error(str(e))
            return 1
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
