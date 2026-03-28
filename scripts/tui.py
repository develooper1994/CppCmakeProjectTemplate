#!/usr/bin/env python3
"""
tui.py — Terminal User Interface for CppCmakeProjectTemplate tooling.

Requires: pip3 install textual --break-system-packages

Usage:
    python3 scripts/tui.py [--preset <preset>]
    # or via tool dispatcher:
    python3 scripts/tool.py tui [--preset <preset>]

Priority order for preset value:
    interactive (widget change) > --preset CLI arg > session file > default

Session is persisted to .tui_session.json in project root.
All operations use DIRECT IMPORTS — no subprocess calls between Python modules.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, ScrollableContainer
    from textual.screen import Screen
    from textual.widgets import (
        Button, Footer, Header, Input, Label,
        Select, Static, TabbedContent, TabPane,
    )
except ImportError:
    print("Textual not installed. Run: pip3 install textual --break-system-packages")
    sys.exit(1)

# ── Path bootstrap ────────────────────────────────────────────────────────────
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build     as _build    # scripts/build.py
import toollib   as _lib      # scripts/toollib.py
import toolsolution as _sol   # scripts/toolsolution.py

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_FILE = PROJECT_ROOT / ".tui_session.json"
_DEFAULT_PRESET = "gcc-debug-static-x86_64"


# ── Session helpers ───────────────────────────────────────────────────────────
# Priority: interactive (widget change) > CLI --preset arg > session file > default

def _load_session() -> dict:
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_session(data: dict) -> None:
    try:
        existing = _load_session()
        existing.update(data)
        SESSION_FILE.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def _initial_preset(cli_arg: str | None) -> str:
    """Resolve initial preset: CLI arg > session > default."""
    if cli_arg:
        return cli_arg
    return _load_session().get("last_preset", _DEFAULT_PRESET)


# ── Direct-call helpers (no subprocess) ──────────────────────────────────────

def _capture(fn, *args, **kwargs) -> str:
    """Call fn(*args, **kwargs), capture stdout+stderr, return as string."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            fn(*args, **kwargs)
        except SystemExit:
            pass
        except Exception as e:
            buf.write(f"\n❌ Exception: {e}\n")
    out = buf.getvalue().strip()
    # Strip ANSI codes for clean TUI display
    import re
    out = re.sub(r'\x1b\[[0-9;]*m', '', out)
    return out if out else "(no output)"


def _ns(**kwargs) -> SimpleNamespace:
    """Build a SimpleNamespace (argparse.Namespace substitute)."""
    ns = SimpleNamespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


# ── Output screen ─────────────────────────────────────────────────────────────

class OutputScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back"),
                Binding("q",      "app.pop_screen", "Back")]

    def __init__(self, title: str, output: str) -> None:
        super().__init__()
        self._title  = title
        self._output = output

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(Static(self._output, id="out"))
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._title


# ── Main App ──────────────────────────────────────────────────────────────────

class CppTemplateTUI(App):
    """CppCmakeProjectTemplate TUI — direct imports, no subprocess."""

    CSS = """
    Screen { background: $surface; }
    #main  { padding: 1 2; }
    #result {
        border: solid $primary;
        height: 1fr;
        padding: 1;
        overflow-y: scroll;
    }
    .section-title { color: $accent; text-style: bold; margin-bottom: 1; }
    .row  { height: auto; margin-bottom: 1; }
    Input  { margin-bottom: 1; }
    Select { margin-bottom: 1; }
    """

    BINDINGS = [
        Binding("q",      "quit",         "Quit"),
        Binding("ctrl+l", "clear_output", "Clear"),
    ]

    TITLE     = "CppCmakeProjectTemplate TUI"
    SUB_TITLE = "interactive > cli args > session"

    def __init__(self, initial_preset: str = _DEFAULT_PRESET) -> None:
        super().__init__()
        self._initial_preset = initial_preset

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():

            # Build tab
            with TabPane("🔨 Build", id="tab-build"):
                with Vertical(id="main"):
                    yield Label("Build Operations", classes="section-title")
                    yield Select(
                        options=[
                            ("gcc-debug-static-x86_64",     "gcc-debug-static-x86_64"),
                            ("gcc-release-static-x86_64",   "gcc-release-static-x86_64"),
                            ("clang-debug-static-x86_64",   "clang-debug-static-x86_64"),
                            ("clang-release-static-x86_64", "clang-release-static-x86_64"),
                            ("msvc-debug-static-x64",       "msvc-debug-static-x64"),
                            ("msvc-release-static-x64",     "msvc-release-static-x64"),
                        ],
                        allow_blank=False,
                        id="build-preset",
                    )
                    with Horizontal(classes="row"):
                        yield Button("▶ Build",      id="btn-build",     variant="primary")
                        yield Button("✔ Check",      id="btn-check",     variant="success")
                        yield Button("🗑 Clean",     id="btn-clean")
                        yield Button("🗑 Clean All", id="btn-clean-all")
                        yield Button("📦 Extension", id="btn-extension")
                    yield Static("", id="result")

            # Libraries tab
            with TabPane("📚 Libraries", id="tab-libs"):
                with Vertical(id="main"):
                    yield Label("Library Management", classes="section-title")
                    with Horizontal(classes="row"):
                        yield Button("📋 List",   id="btn-lib-list")
                        yield Button("🌳 Tree",   id="btn-lib-tree")
                        yield Button("🩺 Doctor", id="btn-lib-doctor", variant="warning")

                    yield Label("Add Library:")
                    yield Input(placeholder="name (lowercase_underscore)", id="lib-name")
                    with Horizontal(classes="row"):
                        yield Select(
                            options=[("Normal","normal"),("Header-only","header-only"),
                                     ("Interface","interface")],
                            allow_blank=False, id="lib-type",
                        )
                        yield Select(
                            options=[("No template",""),("Singleton","singleton"),
                                     ("Pimpl","pimpl"),("Observer","observer"),("Factory","factory")],
                            allow_blank=False, id="lib-template",
                        )
                    yield Input(placeholder="deps (comma-separated, optional)", id="lib-deps")
                    with Horizontal(classes="row"):
                        yield Button("➕ Add",     id="btn-lib-add",    variant="primary")
                        yield Button("🔍 Dry-run", id="btn-lib-dry")

                    yield Label("Remove Library:")
                    yield Input(placeholder="library name to remove", id="lib-remove-name")
                    with Horizontal(classes="row"):
                        yield Button("🗑 Remove (detach)",  id="btn-lib-remove")
                        yield Button("💥 Remove + Delete", id="btn-lib-delete", variant="error")

                    yield Label("Export (find_package support):")
                    yield Input(placeholder="library name", id="lib-export-name")
                    yield Button("📤 Export", id="btn-lib-export", variant="success")
                    yield Static("", id="result")

            # Project tab
            with TabPane("⚙ Project", id="tab-project"):
                with Vertical(id="main"):
                    yield Label("Project Orchestration", classes="section-title")
                    with Horizontal(classes="row"):
                        yield Button("📋 Targets",    id="btn-target-list")
                        yield Button("📋 Presets",    id="btn-preset-list")
                        yield Button("🔧 Toolchains", id="btn-tc-list")
                        yield Button("🌐 Repo",       id="btn-repo-list")
                        yield Button("📊 Versions",   id="btn-repo-versions")

                    yield Label("C++ Standard (solution-wide):")
                    with Horizontal(classes="row"):
                        yield Select(
                            options=[("C++14","14"),("C++17","17"),
                                     ("C++20","20"),("C++23","23")],
                            allow_blank=False, id="std-select",
                        )
                        yield Button("⬆ Upgrade Std", id="btn-upgrade-std", variant="primary")

                    yield Label("Config key / value:")
                    with Horizontal(classes="row"):
                        yield Input(placeholder="key (e.g. ENABLE_ASAN)", id="cfg-key")
                        yield Input(placeholder="value (e.g. ON)",        id="cfg-val")
                        yield Button("Set", id="btn-cfg-set", variant="primary")

                    with Horizontal(classes="row"):
                        yield Button("🩺 Doctor", id="btn-sol-doctor", variant="warning")
                        yield Button("🚀 CI",     id="btn-ci",         variant="success")
                    yield Static("", id="result")

            # Info tab
            with TabPane("ℹ Info", id="tab-info"):
                with Vertical(id="main"):
                    yield Label("Library Info & Tests", classes="section-title")
                    yield Input(placeholder="library name", id="info-lib-name")
                    with Horizontal(classes="row"):
                        yield Button("🔍 Info",       id="btn-info-lib")
                        yield Button("▶ Run Tests",   id="btn-info-test", variant="success")
                    yield Static("", id="result")

        yield Footer()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        try:
            sel   = self.query_one("#build-preset", Select)
            valid = [v for _, v in sel._options]  # type: ignore[attr-defined]
            if self._initial_preset in valid:
                sel.value = self._initial_preset
        except Exception:
            pass

    # ── Session save on interactive change (highest priority) ─────────────────

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "build-preset" and event.value is not Select.NULL:
            _save_session({"last_preset": str(event.value)})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _preset(self) -> str:
        try:
            v = self.query_one("#build-preset", Select).value
            if v is not Select.NULL:
                return str(v)
        except Exception:
            pass
        return self._initial_preset

    def _show(self, output: str, title: str = "Output") -> None:
        try:
            self.query_one("#result", Static).update(output)
        except Exception:
            pass
        if len(output) > 2000:
            self.push_screen(OutputScreen(title, output))

    # ── Button handlers (all use direct imports) ───────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:  # noqa: C901
        bid    = event.button.id
        preset = self._preset()

        # ── Build tab ─────────────────────────────────────────────────────────
        if bid == "btn-build":
            out = _capture(_build.cmd_build,
                           _ns(preset=preset))
            self._show(out, "Build")

        elif bid == "btn-check":
            out = _capture(_build.cmd_check,
                           _ns(preset=preset, no_sync=True))
            self._show(out, "Check")

        elif bid == "btn-clean":
            out = _capture(_build.cmd_clean, _ns(targets=[], all=False))
            self._show(out, "Clean")

        elif bid == "btn-clean-all":
            out = _capture(_build.cmd_clean, _ns(targets=[], all=True))
            self._show(out, "Clean All")

        elif bid == "btn-extension":
            out = _capture(_build.cmd_extension,
                           _ns(install=False, publish=False))
            self._show(out, "Extension")

        # ── Libraries — inspect ───────────────────────────────────────────────
        elif bid == "btn-lib-list":
            self._show(_capture(_lib.cmd_list,   _ns()), "Libraries")
        elif bid == "btn-lib-tree":
            self._show(_capture(_lib.cmd_tree,   _ns()), "Dep Tree")
        elif bid == "btn-lib-doctor":
            self._show(_capture(_lib.cmd_doctor, _ns()), "Doctor")

        # ── Libraries — add ───────────────────────────────────────────────────
        elif bid in ("btn-lib-add", "btn-lib-dry"):
            name = self.query_one("#lib-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name first."); return
            lib_type = self.query_one("#lib-type", Select).value
            tmpl     = self.query_one("#lib-template", Select).value
            deps     = self.query_one("#lib-deps", Input).value.strip()
            dry      = (bid == "btn-lib-dry")
            ns = _ns(
                name=name,
                version="1.0.0",
                namespace=name,
                deps=deps,
                cxx_standard="",
                link_app=False,
                dry_run=dry,
                header_only=(lib_type == "header-only"),
                interface=(lib_type == "interface"),
                template=tmpl or "",
            )
            self._show(_capture(_lib.cmd_add, ns), f"Add {name}")

        # ── Libraries — remove ────────────────────────────────────────────────
        elif bid in ("btn-lib-remove", "btn-lib-delete"):
            name = self.query_one("#lib-remove-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name first."); return
            self._show(_capture(_lib.cmd_remove,
                                _ns(name=name, delete=(bid=="btn-lib-delete"), dry_run=False)),
                       f"Remove {name}")

        # ── Libraries — export ────────────────────────────────────────────────
        elif bid == "btn-lib-export":
            name = self.query_one("#lib-export-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name first."); return
            self._show(_capture(_lib.cmd_export, _ns(name=name, dry_run=False)),
                       f"Export {name}")

        # ── Project tab ───────────────────────────────────────────────────────
        elif bid == "btn-target-list":
            self._show(_capture(_sol.cmd_target_list, _ns()), "Targets")
        elif bid == "btn-preset-list":
            self._show(_capture(_sol.cmd_preset_list, _ns()), "Presets")
        elif bid == "btn-tc-list":
            self._show(_capture(_sol.cmd_toolchain_list, _ns()), "Toolchains")
        elif bid == "btn-repo-list":
            self._show(_capture(_sol.cmd_repo_list, _ns()), "Repos")
        elif bid == "btn-repo-versions":
            self._show(_capture(_sol.cmd_repo_versions, _ns()), "Versions")
        elif bid == "btn-upgrade-std":
            std = str(self.query_one("#std-select", Select).value)
            self._show(_capture(_sol.cmd_upgrade_std,
                                _ns(std=std, target=None, dry_run=True)),
                       f"Upgrade C++{std}")
        elif bid == "btn-cfg-set":
            key = self.query_one("#cfg-key", Input).value.strip()
            val = self.query_one("#cfg-val", Input).value.strip()
            if not key or not val:
                self._show("⚠ Enter key and value."); return
            self._show(_capture(_sol.cmd_config_set, _ns(key=key, value=val)), "Config")
        elif bid == "btn-sol-doctor":
            self._show(_capture(_sol.cmd_doctor, _ns()), "Doctor")
        elif bid == "btn-ci":
            filt = preset.split("-")[0]
            self._show(_capture(_sol.cmd_ci,
                                _ns(preset_filter=filt, fail_fast=False)),
                       "CI")

        # ── Info tab ─────────────────────────────────────────────────────────
        elif bid == "btn-info-lib":
            name = self.query_one("#info-lib-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name."); return
            self._show(_capture(_lib.cmd_info, _ns(name=name)), f"Info: {name}")

        elif bid == "btn-info-test":
            name = self.query_one("#info-lib-name", Input).value.strip()
            if not name:
                self._show("⚠ Enter a library name."); return
            self._show(_capture(_lib.cmd_test, _ns(name=name, preset=preset)),
                       f"Test: {name}")

    def action_clear_output(self) -> None:
        try:
            self.query_one("#result", Static).update("")
        except Exception:
            pass


# ── CLI entry point ───────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tui",
        description="Terminal UI (interactive > cli > session > default)",
    )
    parser.add_argument(
        "--preset", default=None,
        help="Initial build preset (overrides session, overridden by interactive selection)",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    initial = _initial_preset(args.preset)
    CppTemplateTUI(initial_preset=initial).run()


if __name__ == "__main__":
    main()
