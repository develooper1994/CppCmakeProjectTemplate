#!/usr/bin/env python3
"""
core/commands/security.py — Security audit and CVE scanning.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from core.utils.common import (
    Logger,
    GlobalConfig,
    CLIResult,
    run_proc,
    run_capture,
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
            import subprocess, shlex
            subprocess.run(shlex.split(install_cmd), check=True)
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
            osv_cmd = ["osv-scanner", "-r", str(PROJECT_ROOT)]
            fmt = getattr(args, 'format', 'text')
            if fmt == "json":
                osv_cmd.extend(["--format", "json"])
            try:
                # Run and capture output so we can evaluate policy thresholds later
                out, rc = run_capture(osv_cmd)
                log_path = PROJECT_ROOT / "build" / "build_logs" / "security_scan_osv.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(out + "\n", encoding="utf-8")
                if rc == 0:
                    Logger.success("OSV-Scanner: Completed (no blocking errors).")
                else:
                    Logger.warn("OSV-Scanner: Completed with issues (check log)")
                    if not args.force:
                        # continue to policy check below which may fail the job
                        pass
            except SystemExit:
                Logger.error("OSV-Scanner encountered an error.")
                if not args.force:
                    raise

    # 2. Static Security Audit (Cppcheck focused on security)
    if not args.no_static:
        if _check_tool("cppcheck", "sudo apt install cppcheck"):
            Logger.info("Running Cppcheck (Security Focus)...")
            checks = getattr(args, 'cppcheck_checks', 'full')
            if getattr(args, 'fast', False):
                checks = "minimal"

            # Auto-detect jobs unless user set --cppcheck-jobs
            jobs = getattr(args, 'cppcheck_jobs', 0)
            if jobs <= 0:
                jobs = max(1, os.cpu_count() or 1)

            cmd = [
                "cppcheck",
                "--inline-suppr",
                "--suppress=missingIncludeSystem",
                "-j", str(jobs),
                "-i", "build",
                "-i", "extension/templates",
            ]

            # Cppcheck build-dir caching: reuse previous analysis of unchanged TUs.
            cppcheck_builddir = PROJECT_ROOT / "build" / "cppcheck-cache"
            cppcheck_builddir.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--cppcheck-build-dir=" + str(cppcheck_builddir)])

            if checks == "full":
                cmd.extend([
                    "--enable=warning,style,performance,portability",
                    "--inconclusive",
                    "--force",
                ])
            else:
                # Faster CI-friendly mode with reduced signal/noise cost.
                cmd.extend([
                    "--enable=warning,performance,portability",
                    "--force",
                ])

            compile_db = PROJECT_ROOT / "build" / "compile_commands.json"
            if compile_db.exists():
                cmd.append("--project=" + str(compile_db))
                # Narrow scope when requested, while still using compile database.
                for p in getattr(args, 'cppcheck_paths', []) or []:
                    rel = Path(p)
                    if not rel.is_absolute():
                        rel = PROJECT_ROOT / rel
                    rel_str = rel.resolve().as_posix()
                    cmd.append("--file-filter=" + rel_str + "/*")
                    cmd.append("--file-filter=" + rel_str + "/**")
            else:
                scoped_paths = getattr(args, 'cppcheck_paths', []) or []
                if scoped_paths:
                    cmd.extend([str((PROJECT_ROOT / p).resolve()) for p in scoped_paths])
                else:
                    cmd.append(str(PROJECT_ROOT))
            # Add user-provided suppressions file (or fall back to project default)
            suppressions = getattr(args, 'suppressions', None)
            if not suppressions:
                default_supp = PROJECT_ROOT / ".cppcheck-suppressions.txt"
                if default_supp.exists():
                    suppressions = str(default_supp)
            if suppressions:
                supp_path = Path(suppressions)
                if supp_path.exists():
                    cmd.extend(["--suppressions-list=" + str(supp_path)])
                else:
                    Logger.warn(f"Suppressions file not found: {suppressions}")
            try:
                out, rc = run_capture(cmd)
                cpp_log = PROJECT_ROOT / "build" / "build_logs" / "security_scan_cppcheck.log"
                cpp_log.parent.mkdir(parents=True, exist_ok=True)
                cpp_log.write_text(out + "\n", encoding="utf-8")
                if rc == 0:
                    Logger.success("Cppcheck Security Audit: OK")
                else:
                    Logger.warn("Cppcheck Security Audit: Issues found (check log)")
                    if not args.force:
                        # continue; policy enforcement below decides exit
                        pass
            except SystemExit:
                Logger.error("Cppcheck Security Audit: Found issues.")
                if not args.force:
                    raise

    # After running scanners, consolidate logs and optionally enforce policy
    try:
        combined = []
        for p in (PROJECT_ROOT / "build" / "build_logs").glob("security_scan_*.log"):
            try:
                combined.append(p.read_text(encoding='utf-8'))
            except Exception:
                pass
        combined_path = PROJECT_ROOT / "build" / "build_logs" / "security_scan_combined.log"
        combined_path.write_text("\n\n".join(combined) + "\n", encoding='utf-8')
        # If caller requested fail-on-severity, evaluate policy script
        if getattr(args, 'fail_on_severity', None):
            # run policy and map threshold
            policy_script = PROJECT_ROOT / "scripts" / "ci" / "ci_security_policy.py"
            if policy_script.exists():
                rc = run_proc([sys.executable, str(policy_script), str(combined_path)], check=False)
                # If user asked to fail on CRITICAL only, require rc == 2; otherwise rc >=1 fail
                if args.fail_on_severity == 'CRITICAL' and rc == 2:
                    Logger.error("Policy enforcement: CRITICAL findings -> failing.")
                    raise SystemExit(2)
                if args.fail_on_severity != 'CRITICAL' and rc >= 1:
                    Logger.error("Policy enforcement: HIGH/CRITICAL findings -> failing.")
                    raise SystemExit(rc if rc else 1)
    except SystemExit:
        raise
    except Exception:
        Logger.warn("Policy evaluation step failed; continuing without policy enforcement.")

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
    p.add_argument("--fail-on-severity", choices=["CRITICAL","HIGH","MEDIUM","LOW"], default=None,
                   help="Fail the command when findings of given minimum severity are detected")
    p.add_argument("--format", choices=["json", "text"], default="text",
                   help="Output format for scan results (default: text)")
    p.add_argument("--suppressions", default=None, metavar="FILE",
                   help="Path to a suppressions file for cppcheck")
    p.add_argument("--cppcheck-jobs", type=int, default=0, metavar="N",
                   help="Cppcheck parallel jobs (0=auto)")
    p.add_argument("--cppcheck-checks", choices=["full", "minimal"], default="full",
                   help="Cppcheck check profile: full or minimal (faster)")
    p.add_argument("--cppcheck-paths", nargs="+", default=[], metavar="PATH",
                   help="Limit cppcheck to specific project paths (for incremental scans)")
    p.add_argument("--fast", action="store_true",
                   help="Enable faster static scan profile (equivalent to --cppcheck-checks minimal)")
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
