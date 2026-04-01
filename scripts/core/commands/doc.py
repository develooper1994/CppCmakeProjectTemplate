#!/usr/bin/env python3
"""
core/commands/doc.py — Documentation utilities.

Commands
--------
  tool doc serve [--port N] [--open]   Serve docs/ locally via HTTP
  tool doc list                        List all docs/*.md files
  tool doc build                       Build HTML docs with mkdocs or sphinx (if configured)
"""
from __future__ import annotations

import argparse
import http.server
import os
import threading
import webbrowser
from pathlib import Path
from core.utils.common import Logger, CLIResult, PROJECT_ROOT

DOCS_DIR = PROJECT_ROOT / "docs"


def _cmd_serve(args) -> CLIResult:
    """Serve the docs/ directory over HTTP."""
    from core.utils.common import GlobalConfig
    port: int = getattr(args, "port", None)
    if port is None:
        port = GlobalConfig.DOC_SERVE_PORT
    open_browser: bool = getattr(args, "open", None)
    if open_browser is None:
        open_browser = GlobalConfig.DOC_SERVE_OPEN

    if not DOCS_DIR.exists():
        return CLIResult(success=False, code=1, message=f"docs/ directory not found: {DOCS_DIR}")

    # Simple handler serving from docs/
    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(DOCS_DIR), **kw)

        def log_message(self, fmt, *args):  # suppress access log spam
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{port}"
    Logger.info(f"Serving docs at {url}  (Ctrl+C to stop)")
    Logger.info(f"Docs directory: {DOCS_DIR}")

    if open_browser:
        # Open browser slightly after server starts
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        Logger.info("Doc server stopped.")

    return CLIResult(success=True, message=f"Doc server stopped")


def _cmd_list(args) -> CLIResult:
    """List all documentation files."""
    if not DOCS_DIR.exists():
        return CLIResult(success=False, code=1, message="docs/ directory not found")

    docs = sorted(DOCS_DIR.glob("**/*.md"))
    Logger.info(f"{'Document':<45} {'Size':>10}")
    Logger.info("-" * 57)
    for d in docs:
        size = d.stat().st_size
        Logger.info(f"{str(d.relative_to(PROJECT_ROOT)):<45} {size:>8} B")
    Logger.info(f"\nTotal: {len(docs)} documents")
    return CLIResult(success=True, message=f"Found {len(docs)} docs", data=[str(d) for d in docs])


def _cmd_build(args) -> CLIResult:
    """Build HTML documentation using mkdocs or sphinx."""
    import shutil
    from core.utils.common import run_proc

    if shutil.which("mkdocs"):
        # Check for mkdocs.yml
        cfg = PROJECT_ROOT / "mkdocs.yml"
        if cfg.exists():
            Logger.info("Building with mkdocs...")
            rc = run_proc(["mkdocs", "build", "--site-dir", str(PROJECT_ROOT / "site")], check=False)
            return CLIResult(success=(rc == 0), code=rc, message="mkdocs build done")
        Logger.warning("mkdocs found but no mkdocs.yml — skipping")

    if shutil.which("sphinx-build"):
        conf = PROJECT_ROOT / "docs" / "conf.py"
        if conf.exists():
            Logger.info("Building with sphinx...")
            out = PROJECT_ROOT / "docs" / "_build" / "html"
            rc = run_proc(["sphinx-build", str(DOCS_DIR), str(out)], check=False)
            return CLIResult(success=(rc == 0), code=rc, message="sphinx build done")
        Logger.warning("sphinx found but no docs/conf.py — skipping")

    # Fallback: just list the docs
    Logger.info("No mkdocs or sphinx configured. Listing docs instead.")
    return _cmd_list(args)


def doc_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool doc", description="Documentation utilities")
    sub = parser.add_subparsers(dest="subcommand")

    # serve
    p = sub.add_parser("serve", help="Serve docs/ locally via HTTP")
    p.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    p.add_argument("--open", action="store_true", help="Open browser automatically")
    p.set_defaults(func=_cmd_serve)

    # list
    p = sub.add_parser("list", help="List all documentation files")
    p.set_defaults(func=_cmd_list)

    # build
    p = sub.add_parser("build", help="Build HTML docs with mkdocs or sphinx")
    p.set_defaults(func=_cmd_build)

    return parser


def main(argv: list[str]) -> None:
    parser = doc_parser()
    args = parser.parse_args(argv if argv else [])
    if hasattr(args, "func"):
        args.func(args).exit()
    else:
        parser.print_help()
