"""core/commands/license.py — license recommendation and application helpers."""
from __future__ import annotations

import argparse
import re
import sys

from core.utils.common import Logger, PROJECT_ROOT

SUPPORTED_LICENSES = {
    "MIT": "Short, permissive, minimal obligations.",
    "Apache-2.0": "Permissive with an explicit patent grant.",
    "BSD-3-Clause": "Permissive with a non-endorsement clause.",
    "MPL-2.0": "File-level copyleft — good middle ground for shared changes.",
    "GPL-3.0-only": "Strong copyleft for full-project share-alike requirements.",
    "LGPL-3.0-only": "Weaker copyleft, often suitable for libraries.",
    "Unlicense": "Public-domain style dedication with no attribution requirement.",
}


def _ask_yes_no(prompt: str, *, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    reply = input(f"{prompt} {suffix}: ").strip().lower()
    if not reply:
        return default
    return reply in {"y", "yes"}


def recommend_license(*, copyleft: bool, share_changes: bool, patent_grant: bool, library_mode: bool, public_domain: bool) -> tuple[str, str]:
    """Return a recommended SPDX identifier and a short reason."""
    if public_domain:
        return "Unlicense", "You want the least restriction possible and are comfortable with a public-domain style release."
    if copyleft and share_changes:
        if library_mode:
            return "LGPL-3.0-only", "You want downstream changes to stay open while still allowing broader library adoption."
        return "GPL-3.0-only", "You want strong share-alike obligations for derivative works."
    if share_changes:
        return "MPL-2.0", "You want modifications to shared files to remain open without forcing the whole project under copyleft."
    if patent_grant:
        return "Apache-2.0", "You want a permissive license plus explicit patent protection."
    if copyleft:
        return "GPL-3.0-only", "You asked for copyleft behavior and GPL is the clearest default choice."
    return "MIT", "You want a simple, permissive default with minimal obligations."


def _apply_to_tool_toml(license_id: str) -> None:
    tool_toml = PROJECT_ROOT / "tool.toml"
    text = tool_toml.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^license\s*=\s*".*"\s*$',
        f'license = "{license_id}"',
        text,
        count=1,
    )
    if count != 1:
        Logger.error("Could not update the license field in tool.toml.")
        sys.exit(1)
    tool_toml.write_text(updated, encoding="utf-8")
    Logger.success(f"Updated tool.toml → project.license = {license_id}")


def _run_recommend(args: argparse.Namespace) -> None:
    copyleft = args.copyleft
    share_changes = args.share_changes
    patent_grant = args.patent_grant
    library_mode = args.library
    public_domain = args.public_domain

    if not any([copyleft, share_changes, patent_grant, library_mode, public_domain]) and sys.stdin.isatty():
        public_domain = _ask_yes_no("Do you want a public-domain style release?", default=False)
        if not public_domain:
            copyleft = _ask_yes_no("Do you want strong copyleft / share-alike behavior?", default=False)
            share_changes = _ask_yes_no("Should modifications to covered files stay open?", default=False)
            patent_grant = _ask_yes_no("Is an explicit patent grant important?", default=True)
            library_mode = _ask_yes_no("Is this mainly a reusable library?", default=False)

    license_id, reason = recommend_license(
        copyleft=copyleft,
        share_changes=share_changes,
        patent_grant=patent_grant,
        library_mode=library_mode,
        public_domain=public_domain,
    )

    Logger.info(f"Recommended license: {license_id}")
    Logger.info(reason)
    Logger.info(f"Why this option: {SUPPORTED_LICENSES[license_id]}")

    if args.apply:
        _apply_to_tool_toml(license_id)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tool license",
        description="Recommend and optionally apply a project license.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    recommend_parser = subparsers.add_parser("recommend", help="Recommend a suitable project license.")
    recommend_parser.add_argument("--copyleft", action="store_true", default=False, help="Prefer a copyleft license.")
    recommend_parser.add_argument("--share-changes", action="store_true", default=False, help="Require modifications to shared files to remain open.")
    recommend_parser.add_argument("--patent-grant", action="store_true", default=False, help="Prefer licenses with an explicit patent grant.")
    recommend_parser.add_argument("--library", action="store_true", default=False, help="Optimize the recommendation for reusable libraries.")
    recommend_parser.add_argument("--public-domain", action="store_true", default=False, help="Prefer a public-domain style option.")
    recommend_parser.add_argument("--apply", action="store_true", default=False, help="Write the recommended license back into tool.toml.")

    subparsers.add_parser("list", help="List supported license identifiers.")

    args = parser.parse_args(argv)
    if args.subcommand in (None, "recommend"):
        _run_recommend(args)
        return

    if args.subcommand == "list":
        Logger.info("Supported licenses:")
        for license_id, description in SUPPORTED_LICENSES.items():
            Logger.info(f"  {license_id:14s} → {description}")
        return
