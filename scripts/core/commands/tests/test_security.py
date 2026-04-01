"""Tests for core/commands/security.py — security scan command."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath("scripts"))

from core.commands.security import _check_tool, _impl_cmd_scan, security_parser


# ── _check_tool ───────────────────────────────────────────────────────────────

class TestCheckTool:
    def test_finds_existing_tool(self):
        # 'ls' (or 'true') is always on the PATH
        assert _check_tool("ls", "echo dummy") is True

    def test_missing_tool_without_autoinstall(self):
        result = _check_tool("__tool_that_does_not_exist__",
                             "echo no-op", auto_install=False)
        assert result is False

    def test_missing_tool_with_failing_install(self):
        # Install command will silently fail; tool still absent → False
        result = _check_tool("__tool_that_does_not_exist__",
                             "false", auto_install=True)
        assert result is False


# ── security_parser ───────────────────────────────────────────────────────────

class TestSecurityParser:
    def test_parser_exists(self):
        parser = security_parser()
        assert parser is not None

    def test_default_format_is_text(self):
        parser = security_parser()
        args = parser.parse_args(["scan"])
        assert getattr(args, "format", "text") == "text"

    def test_json_format_flag(self):
        parser = security_parser()
        args = parser.parse_args(["scan", "--format", "json"])
        assert args.format == "json"

    def test_suppressions_flag(self):
        parser = security_parser()
        args = parser.parse_args(["scan", "--suppressions", "/tmp/supp.txt"])
        assert args.suppressions == "/tmp/supp.txt"

    def test_fail_on_severity_choices(self):
        parser = security_parser()
        for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            args = parser.parse_args(["scan", "--fail-on-severity", severity])
            assert args.fail_on_severity == severity

    def test_install_flag(self):
        parser = security_parser()
        args = parser.parse_args(["scan", "--install"])
        assert args.install is True

    def test_force_flag(self):
        parser = security_parser()
        args = parser.parse_args(["scan", "--force"])
        assert args.force is True

    def test_no_osv_flag(self):
        parser = security_parser()
        args = parser.parse_args(["scan", "--no-osv"])
        assert args.no_osv is True

    def test_no_static_flag(self):
        parser = security_parser()
        args = parser.parse_args(["scan", "--no-static"])
        assert args.no_static is True

    def test_combined_flags(self):
        parser = security_parser()
        args = parser.parse_args([
            "scan",
            "--format", "json",
            "--fail-on-severity", "HIGH",
            "--no-osv",
            "--force",
        ])
        assert args.format == "json"
        assert args.fail_on_severity == "HIGH"
        assert args.no_osv is True
        assert args.force is True


# ── _impl_cmd_scan (smoke — tools absent) ────────────────────────────────────

class TestImplCmdScanSmoke:
    """Smoke tests: run with --no-osv --no-static --force so network/tool calls
    are skipped entirely. Validates the command doesn't crash."""

    def _make_args(self, **kwargs):
        defaults = dict(
            no_osv=True,
            no_static=True,
            force=True,
            install=False,
            format="text",
            suppressions=None,
            fail_on_severity=None,
        )
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_smoke_no_scanners(self):
        args = self._make_args()
        # Should complete without raising
        try:
            _impl_cmd_scan(args)
        except SystemExit as e:
            # Allowed to sys.exit(0) on clean run
            assert e.code == 0 or e.code is None
