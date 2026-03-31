#!/usr/bin/env python3
"""
core/commands/security.py — Security audit and CVE scanning.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from core.utils.common import (
    Logger,
    GlobalConfig,
    CLIResult,
    run_proc,
    PROJECT_ROOT,
)

def _check_tool(name: str, install_cmd: str, auto_install: bool = False) -> bool:
    # 1. System Path
    if shutil.which(name):
        return True
    
    # 2. Go Path fallback
    go_bin = Path.home() / "go" / "bin" / name
    if name == "osv-scanner" and go_bin.exists():
        # Update PATH for the current process
        import os
        os.environ["PATH"] += os.pathsep + str(go_bin.parent)
        return True

    if auto_install:
        Logger.info(f"Attempting to install '{name}' using: {install_cmd}")
        try:
            # Split command for run_proc or use shell if it contains pipes/redirects
            import subprocess
            subprocess.run(install_cmd, shell=True, check=True)
            if shutil.which(name):
                Logger.success(f"Successfully installed '{name}'.")
                return True
        except Exception as e:
            Logger.error(f"Failed to install '{name}': {e}")

    Logger.error(f"Required tool '{name}' not found.")
    print(f"\nTo install manually, try:\n  {install_cmd}\n")
    return False

def _impl_cmd_scan(args) -> None:
    # 1. OSV-Scanner (CVE Audit)
    if not args.no_osv:
        install_cmd = "go install github.com/google/osv-scanner/cmd/osv-scanner@latest"
        if _check_tool("osv-scanner", install_cmd, auto_install=args.install):
            Logger.info("Running OSV-Scanner (CVE Audit)...")
            try:
                # Scan project root for manifest files (conanfile.py, vcpkg.json, etc.)
                run_proc(["osv-scanner", "-r", str(PROJECT_ROOT)])
                Logger.success("OSV-Scanner: No known vulnerabilities found.")
            except SystemExit:
                Logger.error("OSV-Scanner found potential vulnerabilities.")
                if not args.force:
                    raise

    # 2. Static Security Audit (Cppcheck focused on security)
    if not args.no_static:
        if _check_tool("cppcheck", "sudo apt install cppcheck"):
            Logger.info("Running Cppcheck (Security Focus)...")
            # Focus on security, warning, and portability
            cmd = [
                "cppcheck",
                "--enable=warning,style,performance,portability",
                "--inconclusive",
                "--force",
                "--inline-suppr",
                "--suppress=missingIncludeSystem",
                "--project=" + str(PROJECT_ROOT / "build" / "compile_commands.json") if (PROJECT_ROOT / "build" / "compile_commands.json").exists() else str(PROJECT_ROOT),
                "-i", "build",
                "-i", "extension/templates"
            ]
            try:
                run_proc(cmd)
                Logger.success("Cppcheck Security Audit: OK")
            except SystemExit:
                Logger.error("Cppcheck Security Audit: Found issues.")
                if not args.force:
                    raise

def cmd_scan(args: argparse.Namespace) -> CLIResult:
    if GlobalConfig.DRY_RUN:
        Logger.info("[DRY-RUN] Would run OSV-Scanner and Cppcheck security audit")
        return CLIResult(success=True, message="[DRY-RUN] security scan skipped")
    try:
        _impl_cmd_scan(args)
        return CLIResult(success=True, message="Security audit complete.")
    except SystemExit as e:
        return CLIResult(success=(e.code == 0), code=e.code or 1, message="Security audit found issues or failed.")

def security_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool security", description="Security and CVE audit tools")
    sub = parser.add_subparsers(dest="subcommand")

    p = sub.add_parser("scan", help="Run full security audit (OSV + Static)")
    p.add_argument("--install", action="store_true", help="Try to install missing tools automatically")
    p.add_argument("--no-osv", action="store_true", help="Skip OSV-Scanner CVE check")
    p.add_argument("--no-static", action="store_true", help="Skip static security analysis")
    p.add_argument("--force", action="store_true", help="Continue even if vulnerabilities are found")
    p.set_defaults(func=cmd_scan)

    return parser

def main(argv: list[str]) -> None:
    parser = security_parser()
    args = parser.parse_args(argv if argv else ["scan"])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
