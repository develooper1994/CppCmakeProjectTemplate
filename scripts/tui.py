#!/usr/bin/env python3
"""
tui.py — Terminal User Interface for CppCmakeProjectTemplate tooling.

Requires: pip install textual

Usage:
    python3 scripts/tui.py

Provides a full-screen TUI that wraps:
  - toollib.py  (library management)
  - toolsolution.py (project orchestration)
  - build.py (build / check / clean)
All operations run CLI tools in a terminal panel — GUI is pure wrapper.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, ScrollableContainer
    from textual.screen import Screen
    from textual.widgets import (
        Button, Footer, Header, Input, Label, ListItem,
        ListView, Log, Pretty, Select, Static, TabbedContent, TabPane,
    )
    from textual.reactive import reactive
except ImportError:
    print("Textual not installed. Run: pip3 install textual --break-system-packages")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLLIB      = Path(__file__).resolve().parent / "toollib.py"
TOOLSOLUTION = Path(__file__).resolve().parent / "toolsolution.py"
BUILD        = Path(__file__).resolve().parent / "build.py"
PYTHON       = sys.executable


def run_tool(cmd: list[str]) -> str:
    """Run a tool subprocess and return combined stdout+stderr."""
    try:
        result = subprocess.run(
            cmd, cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=120,
        )
        out = result.stdout + result.stderr
        return out.strip() if out.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "❌ Timed out after 120s"
    except Exception as e:
        return f"❌ Error: {e}"


# ── Screens ───────────────────────────────────────────────────────────────────

class OutputScreen(Screen):
    """Full-screen output viewer for long commands."""

    BINDINGS = [Binding("escape,q", "app.pop_screen", "Back")]

    def __init__(self, title: str, output: str) -> None:
        super().__init__()
        self._title  = title
        self._output = output

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(Static(self._output, id="output"))
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._title


# ── Main App ──────────────────────────────────────────────────────────────────

class CppTemplateTUI(App):
    """CppCmakeProjectTemplate — Terminal UI"""

    CSS = """
    Screen {
        background: $surface;
    }
    #sidebar {
        width: 28;
        border-right: solid $primary;
        padding: 1;
    }
    #sidebar Button {
        width: 100%;
        margin-bottom: 1;
    }
    #main {
        padding: 1 2;
    }
    #result {
        border: solid $primary;
        height: 1fr;
        padding: 1;
        overflow-y: scroll;
    }
    .section-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    .row {
        height: auto;
        margin-bottom: 1;
    }
    Input {
        margin-bottom: 1;
    }
    Select {
        margin-bottom: 1;
    }
    #status-bar {
        height: 1;
        background: $primary;
        color: $background;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+l", "clear_output", "Clear output"),
    ]

    TITLE = "CppCmakeProjectTemplate TUI"
    SUB_TITLE = "All operations delegate to CLI tools"

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():

            # ── Build tab ────────────────────────────────────────────────────
            with TabPane("🔨 Build", id="tab-build"):
                with Vertical(id="main"):
                    yield Label("Build Operations", classes="section-title")
                    with Horizontal(classes="row"):
                        yield Select(
                            options=[
                                ("gcc-debug-static-x86_64",   "gcc-debug-static-x86_64"),
                                ("gcc-release-static-x86_64", "gcc-release-static-x86_64"),
                                ("clang-debug-static-x86_64", "clang-debug-static-x86_64"),
                                ("msvc-debug-static-x64",     "msvc-debug-static-x64"),
                            ],
                            allow_blank=False,
                            id="build-preset",
                        )
                    with Horizontal(classes="row"):
                        yield Button("▶ Build",        id="btn-build",     variant="primary")
                        yield Button("✔ Check",        id="btn-check",     variant="success")
                        yield Button("🗑 Clean",        id="btn-clean")
                        yield Button("🗑 Clean All",   id="btn-clean-all")
                        yield Button("📦 Extension",   id="btn-extension")
                    yield Static("", id="result")

            # ── Libraries tab ────────────────────────────────────────────────
            with TabPane("📚 Libraries", id="tab-libs"):
                with Vertical(id="main"):
                    yield Label("Library Management", classes="section-title")

                    with Horizontal(classes="row"):
                        yield Button("📋 List",   id="btn-lib-list",   variant="default")
                        yield Button("🌳 Tree",   id="btn-lib-tree",   variant="default")
                        yield Button("🩺 Doctor", id="btn-lib-doctor", variant="warning")

                    yield Label("Add Library:")
                    yield Input(placeholder="library name (lowercase_underscore)", id="lib-name")
                    with Horizontal(classes="row"):
                        yield Select(
                            options=[
                                ("Normal",      "normal"),
                                ("Header-only", "header-only"),
                                ("Interface",   "interface"),
                            ],
                            id="lib-type",
                            allow_blank=False,
                        )
                        yield Select(
                            options=[
                                ("No template", ""),
                                ("Singleton",   "singleton"),
                                ("Pimpl",       "pimpl"),
                                ("Observer",    "observer"),
                                ("Factory",     "factory"),
                            ],
                            id="lib-template",
                            allow_blank=False,
                        )
                    yield Input(placeholder="deps (comma-separated, optional)", id="lib-deps")
                    with Horizontal(classes="row"):
                        yield Button("➕ Add",      id="btn-lib-add",      variant="primary")
                        yield Button("🔍 Dry-run",  id="btn-lib-dry",      variant="default")

                    yield Label("Remove Library:")
                    yield Input(placeholder="library name to remove", id="lib-remove-name")
                    with Horizontal(classes="row"):
                        yield Button("🗑 Remove (detach)", id="btn-lib-remove")
                        yield Button("💥 Remove + Delete", id="btn-lib-delete", variant="error")

                    yield Label("Export (find_package support):")
                    yield Input(placeholder="library name", id="lib-export-name")
                    yield Button("📤 Export", id="btn-lib-export", variant="success")

                    yield Static("", id="result")

            # ── Project tab ──────────────────────────────────────────────────
            with TabPane("⚙ Project", id="tab-project"):
                with Vertical(id="main"):
                    yield Label("Project Orchestration", classes="section-title")

                    with Horizontal(classes="row"):
                        yield Button("📋 Target list", id="btn-target-list")
                        yield Button("📋 Preset list", id="btn-preset-list")
                        yield Button("🔧 Toolchain list", id="btn-tc-list")
                        yield Button("🌐 Repo list", id="btn-repo-list")
                        yield Button("📊 Versions", id="btn-repo-versions")

                    yield Label("C++ Standard (solution-wide):")
                    with Horizontal(classes="row"):
                        yield Select(
                            options=[("C++17", "17"), ("C++20", "20"), ("C++23", "23"), ("C++14", "14")],
                            allow_blank=False,
                            id="std-select",
                        )
                        yield Button("⬆ Upgrade Std", id="btn-upgrade-std", variant="primary")

                    yield Label("Config key/value:")
                    with Horizontal(classes="row"):
                        yield Input(placeholder="key (e.g. ENABLE_ASAN)", id="cfg-key")
                        yield Input(placeholder="value (e.g. ON)", id="cfg-val")
                        yield Button("Set", id="btn-cfg-set", variant="primary")

                    with Horizontal(classes="row"):
                        yield Button("🩺 Solution Doctor", id="btn-sol-doctor", variant="warning")
                        yield Button("🚀 CI (current preset)", id="btn-ci",    variant="success")

                    yield Static("", id="result")

            # ── Info tab ─────────────────────────────────────────────────────
            with TabPane("ℹ Info", id="tab-info"):
                with Vertical(id="main"):
                    yield Label("Quick Info", classes="section-title")
                    yield Input(placeholder="library name", id="info-lib-name")
                    with Horizontal(classes="row"):
                        yield Button("🔍 Info",  id="btn-info-lib")
                        yield Button("▶ Run Tests", id="btn-info-test", variant="success")
                    yield Static("", id="result")

        yield Footer()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _show(self, output: str, title: str = "Output") -> None:
        """Show output inline or push an output screen for long results."""
        tab = self.focused
        # Try to update inline Static
        try:
            result_widget = self.query_one("#result", Static)
            result_widget.update(output)
        except Exception:
            pass
        if len(output) > 1500:
            self.push_screen(OutputScreen(title, output))

    def _lib_name(self) -> str:
        try:
            return self.query_one("#lib-name", Input).value.strip()
        except Exception:
            return ""

    def _build_preset(self) -> str:
        try:
            v = self.query_one("#build-preset", Select).value
            return str(v) if v is not Select.NULL else "gcc-debug-static-x86_64"
        except Exception:
            return "gcc-debug-static-x86_64"

    # ── Button handlers ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id

        # Build tab
        if bid == "btn-build":
            preset = self._build_preset()
            self._show(run_tool([PYTHON, str(BUILD), "build", "--preset", preset]), "Build")
        elif bid == "btn-check":
            preset = self._build_preset()
            self._show(run_tool([PYTHON, str(BUILD), "check", "--no-sync", "--preset", preset]), "Check")
        elif bid == "btn-clean":
            self._show(run_tool([PYTHON, str(BUILD), "clean"]), "Clean")
        elif bid == "btn-clean-all":
            self._show(run_tool([PYTHON, str(BUILD), "clean", "--all"]), "Clean All")
        elif bid == "btn-extension":
            self._show(run_tool([PYTHON, str(BUILD), "extension"]), "Extension")

        # Libs tab — inspect
        elif bid == "btn-lib-list":
            self._show(run_tool([PYTHON, str(TOOLLIB), "list"]), "Libraries")
        elif bid == "btn-lib-tree":
            self._show(run_tool([PYTHON, str(TOOLLIB), "tree"]), "Dependency Tree")
        elif bid == "btn-lib-doctor":
            self._show(run_tool([PYTHON, str(TOOLLIB), "doctor"]), "Doctor")

        # Libs tab — add
        elif bid in ("btn-lib-add", "btn-lib-dry"):
            name = self._lib_name()
            if not name:
                self._show("⚠ Enter a library name first."); return
            lib_type_w = self.query_one("#lib-type", Select)
            template_w = self.query_one("#lib-template", Select)
            deps_w     = self.query_one("#lib-deps", Input)
            cmd = [PYTHON, str(TOOLLIB), "add", name]
            lib_type = lib_type_w.value
            if lib_type == "header-only":
                cmd.append("--header-only")
            elif lib_type == "interface":
                cmd.append("--interface")
            tmpl = template_w.value
            if tmpl:
                cmd += ["--template", tmpl]
            deps = deps_w.value.strip()
            if deps:
                cmd += ["--deps", deps]
            if bid == "btn-lib-dry":
                cmd.append("--dry-run")
            self._show(run_tool(cmd), f"Add {name}")

        # Libs tab — remove
        elif bid in ("btn-lib-remove", "btn-lib-delete"):
            try:
                name = self.query_one("#lib-remove-name", Input).value.strip()
            except Exception:
                name = ""
            if not name:
                self._show("⚠ Enter a library name first."); return
            cmd = [PYTHON, str(TOOLLIB), "remove", name]
            if bid == "btn-lib-delete":
                cmd.append("--delete")
            self._show(run_tool(cmd), f"Remove {name}")

        # Libs tab — export
        elif bid == "btn-lib-export":
            try:
                name = self.query_one("#lib-export-name", Input).value.strip()
            except Exception:
                name = ""
            if not name:
                self._show("⚠ Enter a library name first."); return
            self._show(run_tool([PYTHON, str(TOOLLIB), "export", name]), f"Export {name}")

        # Project tab
        elif bid == "btn-target-list":
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "target", "list"]), "Targets")
        elif bid == "btn-preset-list":
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "preset", "list"]), "Presets")
        elif bid == "btn-tc-list":
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "toolchain", "list"]), "Toolchains")
        elif bid == "btn-repo-list":
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "repo", "list"]), "Repos")
        elif bid == "btn-repo-versions":
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "repo", "versions"]), "Versions")
        elif bid == "btn-upgrade-std":
            std = self.query_one("#std-select", Select).value
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "upgrade-std", "--std", std, "--dry-run"]), f"Upgrade C++{std}")
        elif bid == "btn-cfg-set":
            key = self.query_one("#cfg-key", Input).value.strip()
            val = self.query_one("#cfg-val", Input).value.strip()
            if not key or not val:
                self._show("⚠ Enter key and value."); return
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "config", "set", key, val]), "Config Set")
        elif bid == "btn-sol-doctor":
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "doctor"]), "Doctor")
        elif bid == "btn-ci":
            preset = self._build_preset()
            self._show(run_tool([PYTHON, str(TOOLSOLUTION), "ci", "--preset-filter", preset.split("-")[0]]), "CI")

        # Info tab
        elif bid == "btn-info-lib":
            try:
                name = self.query_one("#info-lib-name", Input).value.strip()
            except Exception:
                name = ""
            if not name:
                self._show("⚠ Enter a library name."); return
            self._show(run_tool([PYTHON, str(TOOLLIB), "info", name]), f"Info: {name}")
        elif bid == "btn-info-test":
            try:
                name = self.query_one("#info-lib-name", Input).value.strip()
            except Exception:
                name = ""
            if not name:
                self._show("⚠ Enter a library name."); return
            self._show(run_tool([PYTHON, str(TOOLLIB), "test", name]), f"Test: {name}")

    def action_clear_output(self) -> None:
        try:
            self.query_one("#result", Static).update("")
        except Exception:
            pass


def main() -> None:
    app = CppTemplateTUI()
    app.run()


if __name__ == "__main__":
    main()
